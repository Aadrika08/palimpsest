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
    """The port branch's commit (local ref, else origin as in CI checkouts); always the recorded deterministic commit."""
    tree = SPEC['trees'][tree_id]
    commit = ports.branch_commit(ROOT, tree['branch'])
    assert commit and commit == tree['port_commit'], (tree_id, tree['branch'], commit, tree['port_commit'])
    return commit


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
    erratum = amendment()['erratum_1']
    added = {(h['file'], h['lines'], h['class']) for h in erratum['hunks'] if h['kind'] == 'added'}
    manifest = {(path, h['spec_lines'], h['class']) for path, f in SPEC['files'].items() for h in f['hunks']}
    assert manifest == listed | added
    assert {(p, h['spec_lines']) for p, f in SPEC['files'].items() for h in f['hunks'] if h.get('erratum')} == \
        {(f, lines) for f, lines, _ in added}
    # Widened ranges are recorded in the erratum with the exact manifest range.
    widened = [h for h in erratum['hunks'] if h['kind'] == 'widened']
    assert {(h['file'], h['range']) for h in widened} == {('scripts/prepare_male_navigation_v2.py', '18-19'),
                                                          ('src/palimpsest/male_recovery_research.py', '113-114')}
    for item in widened:
        hunk = next(h for h in SPEC['files'][item['file']]['hunks'] if h['start'] == int(item['range'].split('-')[0]))
        assert hunk['spec_lines'] == item['lines'] and hunk['start'] + len(hunk['old']) - 1 == int(item['range'].split('-')[1])
    assert {h['class'] for h in erratum['hunks']} <= {'H1', 'H2', 'H3', 'H4'}
    assert erratum['cost_table_changed'] is False


def test_manifest_trees_follow_the_amendment_port_trees():
    declared = {t['id']: t for t in amendment()['port_trees']}
    assert set(SPEC['trees']) == set(declared) == {'T-c', 'T-d', 'T-e', 'T-h', 'T-f'}
    for tree_id, tree in SPEC['trees'].items():
        assert tree['base'] == declared[tree_id]['base']
        assert tree['branch'] == f'port/male-v4-{tree_id.lower()}'
        listed = {p.split(' ')[0] for p in declared[tree_id]['ports']}
        additions = set(amendment()['erratum_1']['tree_additions'].get(tree_id, []))
        assert set(tree['files']) <= listed | additions and additions <= set(tree['files']), tree_id
    # Erratum 1: the reader is ported into T-e so the study-plan pin follows the port, although
    # nothing at 736e0cf imports it; T-f carries the v2 collector its admission compares against.
    assert 'scripts/prepare_male_recovery_data.py' in SPEC['trees']['T-e']['files']
    assert 'scripts/collect_male_navigation_v2.py' in SPEC['trees']['T-f']['files']
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
    changed = git(ROOT, 'diff', '--no-renames', '--name-only', tree['base'], port_rev(tree_id)).split()
    assert sorted(changed) == sorted(tree['files'])
    for path in tree['files']:
        base, port = blob(tree['base'], path), blob(port_rev(tree_id), path)
        assert port == ports.apply_hunks(base, SPEC['files'][path]['hunks'], name=path)
        hunks = SPEC['files'][path]['hunks']
        ranges = ports.diff_ranges(ROOT, tree['base'], port_rev(tree_id), path)
        assert ranges and all(ports.contained(first, count, hunks) for first, count in ranges)
        # Every non-empty listed hunk changes something; unchanged lines keep their bytes.
        for hunk in hunks:
            if hunk.get('empty'): continue
            assert any(hunk['start'] - 1 <= first <= hunk['start'] + len(hunk['old']) - 1 for first, _ in ranges)
    assert ports.verify_port(ROOT, SPEC, tree_id, tree['port_commit'])['commit'] == tree['port_commit']


def test_reader_port_is_identical_in_every_tree_that_carries_it():
    payloads = {blob(port_rev(t), 'scripts/prepare_male_recovery_data.py')
                for t in ('T-c', 'T-d', 'T-e', 'T-h', 'T-f')}
    assert len(payloads) == 1
    collectors = {blob(port_rev(t), 'scripts/collect_male_navigation_v2.py') for t in ('T-e', 'T-f')}
    assert len(collectors) == 1


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
            port = blob(port_rev(tree_id), path).decode().split('\n')
            # The relaunch line is byte-identical and still re-executes this very file (the port).
            line = base[hunk['start'] - 1]
            assert hunk['unchanged_line_contains'] in line and line in port
            found[path] = line
    assert set(found) == {'scripts/collect_male_navigation_v2.py', 'scripts/prepare_male_navigation_v2.py'}
    assert '__file__' in found['scripts/collect_male_navigation_v2.py']
    script = blob(port_rev('T-f'), 'scripts/prepare_male_navigation_v2.py').decode()
    assert 'SCRIPT = Path(__file__).resolve()' in script and 'str(SCRIPT)' in found['scripts/prepare_male_navigation_v2.py']
    # The locator reaches both children: bounded_process inherits os.environ and -I keeps non-PYTHON* vars.
    assert not ENV.startswith('PYTHON')
    child = blob(port_rev('T-e'), 'scripts/collect_male_navigation_v2.py').decode()
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
            text = blob(port_rev(tree_id), path).decode()
            found = [s for s in stale if s in text]
            if path == 'scripts/collect_male_navigation.py':
                # v1's own worker/verify keep their inline index path; S0e (v2) never reaches them. In
                # source_pins the two tracked names are only keys mapping to the locator's v4 copies.
                functions = {f.name: f for f in ast.parse(text).body if isinstance(f, ast.FunctionDef)}
                holders = {name for name, f in functions.items()
                           if any(isinstance(c, ast.Constant) and c.value in stale for c in ast.walk(f))}
                assert holders == {'worker', 'verify', 'source_pins'} and not {'worker', 'verify'} & used_from_v1
                keys = [k.value for d in ast.walk(functions['source_pins']) if isinstance(d, ast.Dict) for k in d.keys
                        if isinstance(k, ast.Constant) and '/' in str(k.value)]
                assert keys == ['data/manifests/male-recovery-research-development-v1.json',
                                'docs/plans/m7-recovery-learning-protocol.json']
                assert sorted(found) == ['data/manifests/male-recovery-research-development-v1.json',
                                         'docs/plans/m7-recovery-learning-protocol.json']
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
    for rev, port in ((SPEC['trees'][port_tree]['base'], False), (port_rev(port_tree), True)):
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
    for rev in (SPEC['trees']['T-e']['base'], port_rev('T-e')):
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
    for rev in (SPEC['trees']['T-d']['base'], port_rev('T-d')):
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
    for (rev, port), reader in zip(((SPEC['trees']['T-f']['base'], False), (port_rev('T-f'), True)), readers):
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


# =================================================================== driver: port-branch awareness

import regenerate_male_navigation_v4 as driver  # noqa: E402

DECLARED = json.loads((ROOT/'docs/plans/m7-navigation-v4-pins/declared-fields.json').read_text())


def test_real_port_stages_pin_port_bytes_and_the_s0e_collector_cascade():
    for stage, tree_id in (('S0c', 'T-c'), ('S0d', 'T-d'), ('S0e', 'T-e'), ('S0f', 'T-f')):
        spec, tree = driver.STAGES[stage], SPEC['trees'][tree_id]
        assert spec['port_tree'] == tree_id and spec['commit'] == tree['base']
        assert spec['port_producer_sha256'] == sha(blob(port_rev(tree_id), spec['producer']))
        for rel, pin in spec.get('port_source_guards', {}).items():
            assert rel in tree['files'] and pin == sha(blob(port_rev(tree_id), rel)), (stage, rel)
        assert sorted(spec['port_documents']) == sorted(tree['documents'])
    assert driver.STAGES['S0f']['historical_port_tree'] == 'T-h'
    assert not any('port_tree' in driver.STAGES[s] for s in ('S0a', 'S0b'))
    # :118 cascade: the S0e guard, the T-e port bytes and the staged contact-v2 prior_version value agree.
    collector = sha(blob(port_rev('T-e'), 'scripts/collect_male_navigation.py'))
    assert driver.STAGES['S0e']['port_source_guards'] == {'scripts/collect_male_navigation.py': collector}
    assert driver.STAGES['S0d']['port_source_guards'] == {
        'scripts/prepare_male_recovery_data.py': sha(blob(port_rev('T-d'), 'scripts/prepare_male_recovery_data.py'))}
    assert driver.STAGES['S0f']['port_source_guards'] == {
        'scripts/collect_male_navigation_v2.py': sha(blob(port_rev('T-f'), 'scripts/collect_male_navigation_v2.py'))}
    # Activated before S0e (amendment_1_pending.activated): a port-byte cascade checked against the T-e file.
    field = next(f for f in DECLARED['documents'][driver.CONTACT_V2]['fields'] if f['pointer'] == '/prior_version/collector_sha256')
    assert field['cascade_value'] == collector and field['placeholder'] == 'PENDING-S0e' and field['class'] == 'port-sha256'
    assert driver.CONTACT_V2 in DECLARED['amendment_1_pending']['activated']


def test_study_plan_copy_differs_only_in_its_declared_fields_and_is_filled_with_the_cascades():
    item = DECLARED['documents'][driver.STUDY_PLAN]          # activated before S0e
    original = (ROOT/item['original_path']).read_bytes()
    assert sha(original) == item['original_sha256'] == 'a3612cdc23510fa2b866482e1d13ece123940911ccc2a186c74216c83177e47f'
    copy_bytes = (ROOT/'docs/plans/m7-navigation-v4-pins'/driver.STUDY_PLAN).read_bytes()
    assert driver.field_diff(json.loads(original), json.loads(copy_bytes)) == {f['pointer'] for f in item['fields']}
    doc = json.loads(copy_bytes)
    for field in item['fields']:
        assert field['placeholder'] == 'PENDING-' + field['stage'] and driver.pointer_get(doc, field['pointer']) != field['placeholder']
    driver.check_pin_document(original, copy_bytes, item, consumer=True)
    assert driver.STUDY_PLAN not in DECLARED['amendment_1_pending']['pending_documents']
    assert field_of(item, '/current_reusable_source_sha256/src~1palimpsest~1male_recovery_research.py')['cascade_value'] == \
        sha(blob(port_rev('T-e'), 'src/palimpsest/male_recovery_research.py'))
    assert field_of(item, '/current_reusable_source_sha256/scripts~1prepare_male_recovery_data.py')['cascade_value'] == \
        sha(blob(port_rev('T-e'), 'scripts/prepare_male_recovery_data.py'))
    # Erratum 1: the two document pins are hashed at their v4 copies (locator), so they cascade too.
    for pointer, name in (('/current_reusable_source_sha256/data~1manifests~1male-recovery-research-development-v1.json',
                           driver.RECOVERY_INDEX),
                          ('/current_reusable_source_sha256/docs~1plans~1m7-recovery-learning-protocol.json',
                           driver.RECOVERY_LEARNING)):
        assert field_of(item, pointer)['cascade'] == f'sha256 of the validated v4 copy {name} named in the locator'


def field_of(item, pointer):
    return next(f for f in item['fields'] if f['pointer'] == pointer)


def port_repo(tmp_path):
    """A producing commit, its port branch and a manifest naming it; the repo doubles as the worktree."""
    repo = tmp_path/'repo'; (repo/'scripts').mkdir(parents=True)
    producer = ('import json, os\nfrom pathlib import Path\nimport argparse\n'
                'PIN = {pin}\n'
                'def main(argv=None):\n'
                '    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)\n'
                '    args = parser.parse_args(argv); args.output.mkdir()\n'
                '    (args.output/"result.json").write_text(json.dumps({{"pin": PIN}}))\n')
    (repo/'scripts/fake_port_producer.py').write_text(producer.format(pin="'original-pin'"))
    git(tmp_path, 'init', '-q', str(repo)); git(repo, 'add', '-A'); git(repo, 'commit', '-q', '-m', 'producing')
    base = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'checkout', '-q', '-b', 'port/male-v4-t-x')
    (repo/'scripts/fake_port_producer.py').write_text(producer.format(
        pin=f"json.loads(Path(os.environ['{ENV}']).read_bytes())['schema']"))
    git(repo, 'commit', '-qam', 'port'); port = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'checkout', '-q', '--detach', port)
    manifest = {'schema': ports.SCHEMA, 'protocol_sha256': ports.PROTOCOL_SHA256, 'locator': SPEC['locator'],
                'trees': {'T-x': {'base': base, 'branch': 'port/male-v4-t-x', 'port_commit': port, 'stage': 'S0x',
                                  'files': ['scripts/fake_port_producer.py'], 'documents': []}}}
    stage = {'stage': 'S0x', 'producer': 'scripts/fake_port_producer.py', 'module': 'fake_port_producer', 'commit': base,
             'producer_sha256': sha(git(repo, 'show', f'{base}:scripts/fake_port_producer.py').encode() + b'\n'),
             'port_producer_sha256': sha((repo/'scripts/fake_port_producer.py').read_bytes()), 'port_tree': 'T-x',
             'port_documents': [], 'source_guards': {}, 'documents': [],
             'rebinds': [{'module': 'fake_port_producer', 'attribute': 'PIN', 'kind': 'document-path', 'document': 'x'}],
             'upstream_values': [], 'execution': 'in-process', 'args': {'--output': {'kind': 'output'}}}
    return repo, base, port, manifest, {'S0x': stage}


def test_port_tree_head_must_be_the_expected_port_branch_commit(tmp_path):
    repo, base, port, manifest, _ = port_repo(tmp_path)
    report = driver.verify_port_tree(repo, 'T-x', manifest, repo=repo)
    assert report['head'] == port and report['branch'] == 'port/male-v4-t-x'
    git(repo, 'checkout', '-q', '--detach', base)
    with pytest.raises(driver.Refusal, match='not the port branch commit'):
        driver.verify_port_tree(repo, 'T-x', manifest, repo=repo)
    git(repo, 'checkout', '-q', 'port/male-v4-t-x')
    with pytest.raises(driver.Refusal, match='detached'):
        driver.verify_port_tree(repo, 'T-x', manifest, repo=repo)
    git(repo, 'checkout', '-q', '--detach', port)
    moved = copy.deepcopy(manifest); moved['trees']['T-x']['port_commit'] = base
    with pytest.raises(driver.Refusal, match='branch port/male-v4-t-x is at'):
        driver.verify_port_tree(repo, 'T-x', moved, repo=repo)
    unbuilt = copy.deepcopy(manifest); unbuilt['trees']['T-x']['port_commit'] = None
    with pytest.raises(driver.Refusal, match='no recorded port commit'):
        driver.verify_port_tree(repo, 'T-x', unbuilt, repo=repo)
    git(repo, 'branch', '-q', '-f', 'port/male-v4-t-x', base)
    with pytest.raises(driver.Refusal, match='branch port/male-v4-t-x is at'):
        driver.verify_port_tree(repo, 'T-x', manifest, repo=repo)


def test_plan_only_verifies_the_port_tree_before_planning(tmp_path, capsys):
    repo, base, port, manifest, stages = port_repo(tmp_path)
    argv = ['--stage', 'S0x', '--worktree', str(repo), '--plan-only', '--', '--output', str(tmp_path/'out')]
    run = lambda: driver.main(argv, stages=stages, pins_dir=tmp_path, protocol_sha256=SPEC['protocol_sha256'],
                              ports=manifest, repo=repo)
    assert run() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['status'] == 'admissible' and plan['port_check']['head'] == port
    assert plan['rebinds'] == [] and plan['locator']['env'] == ENV
    assert plan['worktree_check']['producer_sha256'] == stages['S0x']['port_producer_sha256']
    git(repo, 'checkout', '-q', '--detach', base)
    assert run() == 3
    assert 'not the port branch commit' in json.loads(capsys.readouterr().out)['reason']


def test_go_runs_the_port_with_the_locator_and_publishes_a_record(tmp_path, capsys, monkeypatch):
    repo, base, port, manifest, stages = port_repo(tmp_path)
    go = tmp_path/'go.json'
    go.write_text(json.dumps({'decision': 'GO', 'stage': 'S0x', 'protocol_sha256': SPEC['protocol_sha256']}))
    saved = list(sys.path), Path.cwd(), list(sys.argv)
    monkeypatch.delenv(ENV, raising=False)
    try:
        code = driver.main(['--stage', 'S0x', '--worktree', str(repo), '--go', str(go), '--pin-record-out',
                            str(tmp_path/'record.json'), '--', '--output', str(tmp_path/'out')],
                           stages=stages, pins_dir=tmp_path, protocol_sha256=SPEC['protocol_sha256'], ports=manifest, repo=repo)
    finally:
        sys.modules.pop('fake_port_producer', None); sys.path[:] = saved[0]; __import__('os').chdir(saved[1]); sys.argv[:] = saved[2]
    assert code == 0, capsys.readouterr().out
    assert json.loads((tmp_path/'out/result.json').read_text()) == {'pin': SPEC['locator']['schema']}
    record = json.loads((tmp_path/'record.json').read_text())
    assert record['producing_commit'] == port and record['port']['tree'] == 'T-x'
    locator_file = Path(record['port']['locator_path'])
    assert sha(locator_file.read_bytes()) == record['port']['locator_sha256']


def test_real_cli_refuses_a_port_stage_worktree_that_is_not_its_port_branch(tmp_path, capsys):
    repo, *_ = port_repo(tmp_path)
    argv = ['--stage', 'S0c', '--worktree', str(repo), '--previous-pins', str(tmp_path/'never-read.json'), '--plan-only',
            '--', '--output', str(tmp_path/'x')]
    assert driver.main(argv) == 3  # refused at the port check, before the previous record is opened
    assert 'not the port branch commit' in json.loads(capsys.readouterr().out)['reason']


# =================================================================== probe: port entry points

import probe_male_navigation_v4_imports as probe  # noqa: E402


def test_probe_declares_port_entry_points_and_refuses_wrong_head_without_child(tmp_path, monkeypatch):
    table = probe.ENTRYPOINTS
    assert {k: v['port_tree'] for k, v in table.items() if v.get('port_tree')} == {
        'S0c-port': 'T-c', 'S0d-port': 'T-d', 'S0e-port': 'T-e', 'S0f-port': 'T-f', 'S0f-historical-port': 'T-h'}
    assert all(table[k]['module'] == table[k[:-5]]['module'] for k in table if k.endswith('-port'))
    assert probe.port_commit('T-e') == SPEC['trees']['T-e']['port_commit']
    calls = []
    monkeypatch.setattr(probe, 'probe_entry', lambda *a, **k: calls.append((a, k)) or {'status': 'passed'})
    repo, *_ = port_repo(tmp_path)
    result = probe.probe_stage(sys.executable, 'S0c-port', repo)
    assert result['status'] == 'refused' and calls == [] and 'port' in result['reasons'][0]
    monkeypatch.setattr(probe, 'git_head', lambda worktree: SPEC['trees']['T-c']['port_commit'])
    (repo/'scripts/prepare_male_recovery_data.py').write_text('')
    assert probe.probe_stage(sys.executable, 'S0c-port', repo, port_pins=tmp_path/'pins.json')['status'] == 'passed'
    assert calls[0][1]['extra_env'] == {ENV: str(tmp_path/'pins.json')}
    assert probe.probe_stage(sys.executable, 'S0c-port', repo)['status'] == 'refused'  # locator required


# =================================================================== erratum 1 sites

def recovery_rows(n):
    raws, rows = [], []
    state = {'count': 0, 'direction': 1, 'previous_bad_contact': 0}
    for t in range(n):
        action = np.array([.1*t, -.1], dtype=np.float32)
        raws.append({'episode': 0, 'tick': t, 'action': action, 'simulation_time': (t+1)*.02, 'eyes': np.array([True, True]),
                     'recovery_expert_action': action, 'recovery_prefix': True, 'body_contact_counts': np.array([0, 1]),
                     'recovery_teacher_before': np.array([0, 1, 0]), 'recovery_teacher_after': np.array([0, 1, 0]),
                     'recovery_transitions': np.array([0, 0, 0])})
        rows.append({'tick': t, 'action': action.tolist(), 'expert_action': action.tolist(), 'prefix': True, 'callback_count': 10,
                     'contact_counts': [0, 1], 'before': state, 'after': state,
                     'transition': {'started': 0, 'completed': 0, 'old_label_replaced': 0}})
    return raws, {'rows': rows, 'contact_ownership': {}, 'collection_boundary': {}, 'coverage': {'passed': True},
                  'final_state': {'phase': 'paused', 'last_outcome': None}}


def admit_namespaces(locator, recovery):
    entry = locator({LEARNING: learning_doc(V2_BASELINE, V2_DEV, recovery)})[LEARNING]
    stubs = {'recovery': types.SimpleNamespace(bind_action=lambda tick, raw, prefix: prefix, bind_clearance=lambda raw, row, own: 0,
                                               validate_collection=lambda bound, boundary, final: {'passed': True}),
             'male_model': types.SimpleNamespace(features=lambda raw: np.full(388, raw['tick'], dtype=np.float32))}
    return reader_namespaces(entry['path'], entry['sha256'], extra=('admit_rows',), stubs=stubs)


def admitted(result):
    if result[0] != 'ok': return result
    episode, admission = result[1]
    return ('ok', sha(episode['features'].tobytes() + episode['targets'].tobytes()), json.dumps(admission, sort_keys=True))


def test_erratum_admit_rows_full_run_equals_original_and_emits_windows_from_the_pinned_length(locator):
    orig, port = admit_namespaces(locator, V2_RECOVERY)
    expected = admitted(outcome(orig['admit_rows'], *recovery_rows(67), 'rec-a'))
    assert expected[0] == 'ok' and json.loads(expected[2])['windows'] == [32, 32, 3]
    assert admitted(outcome(port['admit_rows'], *recovery_rows(67), 'rec-a')) == expected
    _, port = admit_namespaces(locator, [67, 70])
    result = outcome(port['admit_rows'], *recovery_rows(70), 'rec-b')
    assert result[0] == 'ok' and result[1][1]['windows'] == [32, 32, 6] == windows(70)
    _, port = admit_namespaces(locator, [67, 64])
    assert outcome(port['admit_rows'], *recovery_rows(64), 'rec-b')[1][1]['windows'] == [32, 32]
    _, port = admit_namespaces(locator, [67, 121])
    assert outcome(port['admit_rows'], *recovery_rows(121), 'rec-b')[0] == 'refused'


def collector_constants(rev):
    """Module-level PLAN/PLAN_SHA and the literal profile constants of a collect_male_navigation_v2 blob."""
    ns = {'json': json, 'os': __import__('os'), 'Path': Path}
    extract(blob(rev, 'scripts/collect_male_navigation_v2.py'), (), ns, assigns=('PLAN', 'PLAN_SHA', 'PROFILE', 'PROFILE_SHA'))
    return types.SimpleNamespace(**{k: ns[k] for k in ('PLAN', 'PLAN_SHA', 'PROFILE', 'PROFILE_SHA')}, CASES=CASES)


def test_erratum_s0f_admission_compares_the_report_with_the_v4_contact_copy(tmp_path, locator, stub_storage_modules):
    orig, port, run, documents = s0f_fixture(tmp_path, locator)
    data_v2 = json.loads(Path(port['PROTOCOL']).read_text())
    entries = locator({DATA_V2: data_v2, LEARNING: {}, driver.CONTACT_V2: {'contacts': {}}})
    v4_sha = entries[driver.CONTACT_V2]['sha256']
    tf = SPEC['trees']['T-f']
    ported, original = collector_constants(port_rev('T-f')), collector_constants(tf['base'])
    assert ported.PLAN_SHA == v4_sha and ported.PLAN == entries[driver.CONTACT_V2]['path']
    assert original.PLAN_SHA == '29039e944f49dc1458d918dcd738a32ee5fbf5bfdbbee8fff2cd969e4703bab0'
    docs = copy.deepcopy(documents)
    docs['accepted_collection'].update(study_sha256=v4_sha, profile=ported.PROFILE, contact_profile_sha256=ported.PROFILE_SHA)
    for nav, expected in ((ported, 'ok'), (original, 'refused')):
        port['helpers'] = lambda nav=nav: (None, None, None, None, nav)
        assert outcome(port['admit_collection'], data_v2, docs)[0] == expected


def test_erratum_study_plan_source_pins_hash_the_v4_copies_named_in_the_locator(tmp_path, locator):
    root = tmp_path/'tree'
    tracked = {'data/manifests/male-recovery-research-development-v1.json': b'{"original": "index"}\n',
               'docs/plans/m7-recovery-learning-protocol.json': b'{"original": "learning"}\n',
               'scripts/prepare_male_recovery_data.py': b'reader = 1\n'}
    for rel, payload in tracked.items():
        (root/rel).parent.mkdir(parents=True, exist_ok=True); (root/rel).write_bytes(payload)
    entries = locator({driver.RECOVERY_INDEX: {'v4': 'index'}, LEARNING: {'v4': 'learning'}})
    plan = {'current_reusable_source_sha256': {
                'data/manifests/male-recovery-research-development-v1.json': entries[driver.RECOVERY_INDEX]['sha256'],
                'docs/plans/m7-recovery-learning-protocol.json': entries[LEARNING]['sha256'],
                'scripts/prepare_male_recovery_data.py': sha(tracked['scripts/prepare_male_recovery_data.py'])},
            'generator': {'source_sha256': {}}}
    pins = {}
    for which, rev in (('original', SPEC['trees']['T-e']['base']), ('port', port_rev('T-e'))):
        ns = {'json': json, 'os': __import__('os'), 'Path': Path, 'ROOT': Path('/nonexistent-root'), 'PLAN_SHA': 'plan',
              'plan': lambda root=None: plan,
              'digest': lambda path: sha(Path(path).read_bytes()) if Path(path).exists() else 'absent',
              'source_identity': lambda root: {'runtime': 1}}
        pins[which] = extract(blob(rev, 'scripts/collect_male_navigation.py'), ('source_pins',), ns)['source_pins']
    assert outcome(pins['original'], root) == \
        ('refused', 'ValueError', 'Pinned study reader source differs: data/manifests/male-recovery-research-development-v1.json')
    accepted = outcome(pins['port'], root)
    assert accepted[0] == 'ok' and accepted[1]['plan_sha256'] == 'plan'
    Path(entries[LEARNING]['path']).write_text('{"v4": "changed"}\n')
    assert outcome(pins['port'], root) == \
        ('refused', 'ValueError', 'Pinned study reader source differs: docs/plans/m7-recovery-learning-protocol.json')


# =================================================================== count sub-schema (review of erratum 1)

PENDING = DECLARED['amendment_1_pending']
TEACHER = {'baseline_train': [250, 240, 260, 230, 255, 245, 251, 249], 'dev': [300, 310, 305, 313]}
RECOVERY = {'recovery-north-2100': 70, 'recovery-south-2101': 64}
ADVICE = {case: 400 + i for i, case in enumerate(driver.ADVICE_CASES)}


def count_chain(teacher=None, recovery=None, advice=None):
    entry = lambda counts: {'producing_commit': 'c', 'worktree': '/w', 'output_root': '/o', 'outputs': {}, 'counts': counts}
    return {'S0a': entry(teacher or TEACHER), 'S0b': entry(recovery or RECOVERY), 'S0c': entry(None),
            'S0d': entry(None), 'S0e': entry(advice or ADVICE)}


COUNT_CLASSES = ('count-map', 'count-list', 'window-list')


def count_fields(name):
    """Count fields of a v4 copy: activated (documents block) plus still-pending (amendment_1_pending)."""
    active = DECLARED['documents'].get(name, {}).get('fields', [])
    return [f for f in [*active, *PENDING['pending_fields'].get(name, [])] if f['class'] in COUNT_CLASSES]


def pending_item(name):
    return {'fields': count_fields(name)}


def filled_learning():
    original = json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
    doc = copy.deepcopy(original)
    base, dev = TEACHER['baseline_train'], TEACHER['dev']
    rec = [RECOVERY[s['case_id']] for s in original['recovery_sources']]
    doc['counts'] = {'baseline_train': sum(base), 'dev': sum(dev), 'held_out': 0, 'recovery_train': sum(rec),
                     'train': sum(base) + sum(rec), 'per_source': {'baseline_train': base, 'dev': dev},
                     'v2_reference_counts': original['counts']}
    doc['recovery_ticks_each'] = rec
    doc['recovery_windows'] = [windows(n) for n in rec]
    return original, copy.deepcopy(doc)  # no list/dict shared with the fixtures or the original


def filled_data_v2():
    original = json.loads((ROOT/'docs/plans/m7-navigation-data-v2-protocol.json').read_text())
    doc = copy.deepcopy(original)
    old = TEACHER['baseline_train'] + [RECOVERY[c] for c in driver.RECOVERY_CASES]
    dev, adv = TEACHER['dev'], [ADVICE[c] for c in driver.ADVICE_CASES]
    doc['counts'] = {'old_sources': 14, 'new_sources': 12, 'combined_unique_sources': 26, 'old_train_rows': sum(old),
                     'new_advice_train_rows': sum(adv), 'augmented_train_rows': sum(old) + sum(adv), 'recorded_dev_rows': sum(dev),
                     'combined_rows': sum(old) + sum(adv) + sum(dev), 'held_out_sources': 0, 'held_out_rows': 0,
                     'per_source': {'old_train': old, 'dev': dev, 'advice': adv}, 'v2_reference_counts': original['counts']}
    return original, copy.deepcopy(doc)


def check_counts(name, original, doc, chain):
    driver.check_document_values(name, doc, original, pending_item(name), chain, lambda other: None, ROOT)


def test_every_pending_count_field_names_a_declared_sub_schema():
    schemas = PENDING['count_schemas']
    fields = count_fields(LEARNING) + count_fields(DATA_V2)
    assert {(f['pointer'], f['schema']) for f in fields} == {
        ('/counts', 'recovery-learning-counts-v4'), ('/recovery_ticks_each', 'recovery-ticks-v4'),
        ('/recovery_windows', 'recovery-windows-v4'), ('/counts', 'data-v2-counts-v4')}
    for f in fields:
        schema = schemas[f['schema']]
        assert schema['class'] == f['class'] and schema['traced_from'] and set(schema['traced_from']) <= {'S0a', 'S0b', 'S0e'}
    assert schemas['recovery-learning-counts-v4']['per_source'] == {'baseline_train': 8, 'dev': 4}
    assert schemas['data-v2-counts-v4']['per_source'] == {'old_train': 10, 'dev': 4, 'advice': 12}
    original = json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
    assert [s['case_id'] for s in original['recovery_sources']] == list(driver.RECOVERY_CASES)
    v1 = blob(SPEC['trees']['T-e']['base'], 'scripts/collect_male_navigation.py').decode()
    assert "for scene in range(3100, 3104) for seed in (10, 11, 12)]" in v1
    assert driver.ADVICE_CASES[0] == 'learner-3100-seed-10' and driver.ADVICE_CASES[-1] == 'learner-3103-seed-12'


def test_count_fields_traced_to_the_pin_records_are_accepted():
    check_counts(LEARNING, *filled_learning(), count_chain())
    check_counts(DATA_V2, *filled_data_v2(), count_chain())


LEARNING_MUTATIONS = {
    'reordered_per_source': lambda d: d['counts']['per_source']['baseline_train'].reverse(),
    'current_int_ticks': lambda d: d.update(recovery_ticks_each=67),
    'ticks_reordered': lambda d: d['recovery_ticks_each'].reverse(),
    'windows_not_derived': lambda d: d.update(recovery_windows=[[32, 32, 3], [32, 32, 3]]),
    'sum_inconsistent': lambda d: d['counts'].update(train=d['counts']['train'] + 1),
    'v2_reference_changed': lambda d: d['counts']['v2_reference_counts'].update(train=2118),
    'extra_key': lambda d: d['counts'].update(extra=1),
    'bool_for_int': lambda d: d['counts'].update(held_out=False),
    'pending': lambda d: d.update(recovery_ticks_each='PENDING-S0b'),
}


@pytest.mark.parametrize('mutation', sorted(LEARNING_MUTATIONS))
def test_recovery_learning_count_fields_refuse_untraced_shapes(mutation):
    original, doc = filled_learning()
    LEARNING_MUTATIONS[mutation](doc)
    with pytest.raises(driver.Refusal):
        check_counts(LEARNING, original, doc, count_chain())


@pytest.mark.parametrize('chain, match', [
    (count_chain(recovery={'recovery-north-2100': 70, 'recovery-south-2101': 121}), '120'),
    (count_chain(teacher={'baseline_train': TEACHER['baseline_train'][:7], 'dev': TEACHER['dev']}), 'S0a'),
    (count_chain(teacher={'baseline_train': TEACHER['baseline_train'][:7] + [0], 'dev': TEACHER['dev']}), 'S0a'),
])
def test_recovery_learning_counts_refuse_records_outside_the_structural_invariants(chain, match):
    original, doc = filled_learning()
    with pytest.raises(driver.Refusal, match=match):
        check_counts(LEARNING, original, doc, chain)


@pytest.mark.parametrize('mutation', ['advice_reordered', 'advice_missing', 'advice_over_bound', 'constants', 'record_missing'])
def test_data_v2_counts_refuse_untraced_shapes(mutation):
    original, doc = filled_data_v2()
    chain = count_chain()
    if mutation == 'advice_reordered': doc['counts']['per_source']['advice'].reverse()
    elif mutation == 'advice_missing': doc['counts']['per_source']['advice'].pop()
    elif mutation == 'advice_over_bound':
        chain = count_chain(advice={**ADVICE, driver.ADVICE_CASES[0]: 601})
    elif mutation == 'constants': doc['counts']['combined_unique_sources'] = 25
    else: chain['S0e'].pop('counts')
    with pytest.raises(driver.Refusal):
        check_counts(DATA_V2, original, doc, chain)


def test_stage_counts_read_the_teacher_recovery_and_advice_outputs(tmp_path):
    s0a = tmp_path/'s0a'; s0a.mkdir()
    runs = [{'split': 'train', 'ticks': n} for n in TEACHER['baseline_train']] + [{'split': 'dev', 'ticks': n} for n in TEACHER['dev']]
    (s0a/'collection.json').write_text(json.dumps({'runs': runs}))
    assert driver.stage_counts('teacher-collection', s0a) == TEACHER
    s0b = tmp_path/'s0b'
    for case, n in RECOVERY.items():
        (s0b/case).mkdir(parents=True); (s0b/case/'result.json').write_text(json.dumps({'recorded_ticks': n, 'rows': [{}]*n}))
    assert driver.stage_counts('recovery-cases', s0b) == RECOVERY
    (s0b/'recovery-south-2101'/'result.json').write_text(json.dumps({'recorded_ticks': 64, 'rows': [{}]*63}))
    with pytest.raises(driver.Refusal, match='recorded_ticks'):
        driver.stage_counts('recovery-cases', s0b)
    s0e = tmp_path/'s0e'
    for case, n in ADVICE.items():
        (s0e/case).mkdir(parents=True); (s0e/case/'result.json').write_text(json.dumps({'rows': [{}]*n}))
    assert driver.stage_counts('advice-cases', s0e) == ADVICE
    assert {s: driver.STAGES[s].get('records_counts') for s in driver.STAGES} == {
        'S0a': 'teacher-collection', 'S0b': 'recovery-cases', 'S0c': None, 'S0d': None, 'S0e': 'advice-cases', 'S0f': None}


def test_pin_record_carries_counts_and_the_chain_refuses_tampered_counts(tmp_path):
    out = tmp_path/'out'; out.mkdir(); (out/'collection.json').write_text('{}')
    spec = {'commit': 'c'*40, 'producer_sha256': 'p'*64}
    record = driver.make_pin_record(spec, 'S0a', tmp_path, out, None, protocol_sha256=SPEC['protocol_sha256'], counts=TEACHER)
    assert record['counts'] == record['chain']['S0a']['counts'] == TEACHER
    stages = {'S0a': spec, 'S0b': spec}
    assert driver.check_pin_record(record, 'S0b', stages, protocol_sha256=SPEC['protocol_sha256'])['S0a']['counts'] == TEACHER
    record['counts'] = {**TEACHER, 'dev': [1, 2, 3, 4]}
    with pytest.raises(driver.Refusal, match='chain'):
        driver.check_pin_record(record, 'S0b', stages, protocol_sha256=SPEC['protocol_sha256'])


def test_port_locator_refuses_relative_paths():
    spec = {'port': {'locator_values': []}}
    assert driver.port_locator(spec, {LEARNING: {'path': '/abs/learning.json', 'sha256': 'a'*64}}, {})['documents']
    for bad in ('docs/plans/m7-recovery-learning-protocol.json', './x.json', ''):
        with pytest.raises(driver.Refusal, match='absolute'):
            driver.port_locator(spec, {LEARNING: {'path': bad, 'sha256': 'a'*64}}, {})
    chain = {'S0c': {'output_root': 'relative/out', 'outputs': {'data-manifest.json': {'sha256': 'b'*64, 'bytes': 1}}}}
    with pytest.raises(driver.Refusal, match='absolute'):
        driver.port_locator({'port': {'locator_values': ['data_manifest']}}, {}, chain)


def test_study_plan_redirect_is_exactly_the_two_named_documents(tmp_path, locator):
    """A locator key matching another pinned source's basename never redirects it."""
    port = blob(port_rev('T-e'), 'scripts/collect_male_navigation.py').decode()
    hunk = next(h for h in SPEC['files']['scripts/collect_male_navigation.py']['hunks'] if h['spec_lines'] == '46-47')
    assert "'data/manifests/male-recovery-research-development-v1.json': v4['male-recovery-research-development-v1.json']['path']" in hunk['new'][0]
    assert "'docs/plans/m7-recovery-learning-protocol.json': v4['m7-recovery-learning-protocol.json']['path']" in hunk['new'][0]
    assert all(line in port for line in hunk['new']) and 'Path(name).name' not in port
    root = tmp_path/'tree'; (root/'scripts').mkdir(parents=True)
    (root/'scripts/prepare_male_recovery_data.py').write_bytes(b'tracked reader\n')
    decoy = tmp_path/'decoy.py'; decoy.write_bytes(b'decoy\n')
    entries = locator({driver.RECOVERY_INDEX: {'v4': 'index'}, LEARNING: {'v4': 'learning'}})
    loc = json.loads(Path(__import__('os').environ[ENV]).read_text())
    loc['documents']['prepare_male_recovery_data.py'] = {'path': str(decoy), 'sha256': sha(b'decoy\n')}
    Path(__import__('os').environ[ENV]).write_text(json.dumps(loc))
    plan = {'current_reusable_source_sha256': {
                'data/manifests/male-recovery-research-development-v1.json': entries[driver.RECOVERY_INDEX]['sha256'],
                'docs/plans/m7-recovery-learning-protocol.json': entries[LEARNING]['sha256'],
                'scripts/prepare_male_recovery_data.py': sha(b'tracked reader\n')}, 'generator': {'source_sha256': {}}}
    ns = {'json': json, 'os': __import__('os'), 'Path': Path, 'ROOT': Path('/nonexistent-root'), 'PLAN_SHA': 'plan',
          'plan': lambda root=None: plan, 'digest': lambda path: sha(Path(path).read_bytes()) if Path(path).exists() else 'absent',
          'source_identity': lambda root: {'runtime': 1}}
    source_pins = extract(port, ('source_pins',), ns)['source_pins']
    assert outcome(source_pins, root)[0] == 'ok'
    plan['current_reusable_source_sha256']['scripts/prepare_male_recovery_data.py'] = sha(b'decoy\n')
    assert outcome(source_pins, root)[2] == 'Pinned study reader source differs: scripts/prepare_male_recovery_data.py'


# =================================================================== S0c: recovery-learning copy filled from S0a/S0b records

PINS = ROOT/'docs/plans/m7-navigation-v4-pins'
S0B_RECORD = ROOT/'docs/reports/male-v4-s0b/pin-record.json'
LEARNING_FIELDS = ['/baseline_collection_sha256', '/counts', '/recovery_report_sha256', '/recovery_sources/0/result_sha256',
                   '/recovery_sources/0/run_id', '/recovery_sources/1/result_sha256', '/recovery_sources/1/run_id',
                   '/recovery_ticks_each', '/recovery_windows']


def learning_item():
    return DECLARED['documents'][LEARNING]


def placeholder_copy():
    """The regenerated copy: the original with every declared field at its placeholder."""
    doc = json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
    for f in learning_item()['fields']: driver.pointer_set(doc, f['pointer'], f['placeholder'])
    return (json.dumps(doc, indent=2) + '\n').encode()


def record_chain(outputs_b=None, recovery=None):
    out = lambda *names: {n: {'sha256': sha(n.encode()), 'bytes': 1} for n in names}
    s0b = outputs_b or out('report.json', 'recovery-north-2100/result.json', 'recovery-south-2101/result.json',
                           'recovery-north-2100/aaaa/recording/manifest.json', 'recovery-north-2100/aaaa/snapshots/initial.snp',
                           'recovery-south-2101/bbbb/recording/manifest.json')
    return {'S0a': {'producing_commit': 'a', 'worktree': '/w', 'output_root': '/o/a', 'outputs': out('collection.json', 'runs/x'),
                    'counts': TEACHER},
            'S0b': {'producing_commit': 'b', 'worktree': '/w', 'output_root': '/o/b', 'outputs': s0b, 'counts': recovery or RECOVERY}}


def test_recovery_learning_count_fields_are_active_and_every_field_names_its_fill_source():
    item = learning_item()
    assert [f['pointer'] for f in item['fields']] == LEARNING_FIELDS
    assert LEARNING not in PENDING['pending_fields'] and PENDING['activated'][LEARNING] == ['/counts', '/recovery_ticks_each',
                                                                                          '/recovery_windows']
    for f in item['fields']:
        assert f['class'] in COUNT_CLASSES or f.get('fill'), f['pointer']


def test_fill_derives_every_recovery_learning_field_from_the_s0a_s0b_records_and_the_result_traces():
    raw, original, chain = placeholder_copy(), json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text()), record_chain()
    values = driver.fill_values(LEARNING, learning_item(), json.loads(raw), original, chain)
    assert sorted(values) == sorted(LEARNING_FIELDS)
    assert values['/baseline_collection_sha256'] == sha(b'collection.json') and values['/recovery_report_sha256'] == sha(b'report.json')
    assert values['/recovery_sources/0/result_sha256'] == sha(b'recovery-north-2100/result.json')
    assert (values['/recovery_sources/0/run_id'], values['/recovery_sources/1/run_id']) == ('aaaa', 'bbbb')
    assert values['/recovery_ticks_each'] == [70, 64] and values['/recovery_windows'] == [[32, 32, 6], [32, 32]]
    assert values['/counts']['per_source'] == TEACHER and values['/counts']['train'] == sum(TEACHER['baseline_train']) + 134
    filled = driver.fill_document(raw, learning_item(), values)
    doc = driver.check_pin_document((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_bytes(), filled, learning_item(), consumer=True)
    driver.check_document_values(LEARNING, doc, original, learning_item(), chain, lambda other: None, PINS)


@pytest.mark.parametrize('chain, match', [
    (lambda c: c.pop('S0b'), 'S0b is not in the pin-record chain'),
    (lambda c: c['S0b']['outputs'].pop('report.json'), 'report.json'),
    (lambda c: c['S0b']['outputs'].update({'recovery-north-2100/cccc/recording/manifest.json': {'sha256': 'x', 'bytes': 1}}),
     'exactly one run directory'),
    (lambda c: c['S0b'].update(counts={'recovery-north-2100': 67, 'recovery-south-2101': 121}), '120'),
])
def test_fill_refuses_missing_records_outputs_ambiguous_runs_and_out_of_bound_counts(chain, match):
    c = record_chain(); chain(c)
    original = json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
    with pytest.raises(driver.Refusal, match=match):
        driver.fill_values(LEARNING, learning_item(), json.loads(placeholder_copy()), original, c)


def test_tracked_recovery_learning_copy_is_filled_from_the_committed_s0a_s0b_pin_records():
    record = json.loads(S0B_RECORD.read_bytes())
    stages = driver.port_stages(driver.STAGES, driver.load_ports())
    chain = driver.check_pin_record(record, 'S0c', stages, protocol_sha256=driver.PROTOCOL_SHA256)
    original_raw = (ROOT/learning_item()['original_path']).read_bytes()
    assert sha(original_raw) == learning_item()['original_sha256']
    copy_raw = (PINS/LEARNING).read_bytes()
    doc = driver.check_pin_document(original_raw, copy_raw, learning_item(), consumer=True)    # no PENDING left
    driver.check_document_values(LEARNING, doc, json.loads(original_raw), learning_item(), chain, lambda other: None, PINS)
    assert doc['recovery_ticks_each'] == [67, 67] and doc['recovery_windows'] == [[32, 32, 3], [32, 32, 3]]
    assert doc['counts']['per_source'] == {'baseline_train': [277, 182, 315, 245, 199, 265, 243, 257], 'dev': [189, 338, 319, 382]}
    assert doc['counts']['train'] == 1983 + 134 and doc['counts']['dev'] == 1228 and doc['counts']['held_out'] == 0
    assert [s['run_id'] for s in doc['recovery_sources']] == ['f10998ca8ed246059193ca87a9a19a7b', 'a3a272518cfe41f0971631439ce1e84c']
    assert copy_raw == driver.fill_document(placeholder_copy(), learning_item(),
                                             driver.fill_values(LEARNING, learning_item(), json.loads(placeholder_copy()),
                                                                json.loads(original_raw), chain))


def test_fill_cli_fills_a_placeholder_copy_in_place_from_previous_records_only(tmp_path, capsys):
    pins = tmp_path/'pins'; pins.mkdir()
    (pins/'declared-fields.json').write_bytes((PINS/'declared-fields.json').read_bytes())
    (pins/LEARNING).write_bytes(placeholder_copy())
    tree = tmp_path/'tree'; (tree/'docs/plans').mkdir(parents=True)
    (tree/learning_item()['original_path']).write_bytes((ROOT/learning_item()['original_path']).read_bytes())
    argv = ['--fill-document', LEARNING, '--stage', 'S0c', '--worktree', str(tree), '--previous-pins', str(S0B_RECORD)]
    assert driver.main(argv, pins_dir=pins) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['status'] == 'filled' and out['sha256'] == sha((pins/LEARNING).read_bytes()) and sorted(out['fields']) == sorted(LEARNING_FIELDS)
    assert (pins/LEARNING).read_bytes() == (PINS/LEARNING).read_bytes()
    assert driver.main(argv, pins_dir=pins) == 3 and 'no placeholder' in json.loads(capsys.readouterr().out)['reason']
    assert driver.main([*argv[:2], '--stage', 'S0b', *argv[4:]], pins_dir=pins) == 3   # S0b does not consume this copy


# =================================================================== S0e: index, study-plan and contact-v2 copies filled from S0c/S0d

INDEX, CONTACT, STUDY = driver.RECOVERY_INDEX, driver.CONTACT_V2, driver.STUDY_PLAN
CASCADES = ('doc-path', 'doc-sha256', 'port-sha256')
S0D_EVIDENCE = ROOT/'docs/reports/male-v4-s0d'
S0D_ROOT = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d')
S0D_RECORDS = [S0D_ROOT/f'control/pairs/seed-{s}/pin-record.json' for s in (10, 11, 12)]
TE_TREE = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e')
TD_TREE = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d')


def item_of(name): return DECLARED['documents'][name]


def placeholders(name):
    item = item_of(name)
    doc = json.loads((ROOT/item['original_path']).read_text())
    for f in item['fields']: driver.pointer_set(doc, f['pointer'], f['placeholder'])
    return doc


def test_s0e_documents_are_active_and_every_field_has_a_fill_source_or_cascade():
    assert {INDEX, CONTACT, STUDY} <= set(DECLARED['documents']) and STUDY not in PENDING['pending_documents']
    assert INDEX not in PENDING['pending_fields'] and CONTACT not in PENDING['pending_fields']
    for name in (INDEX, CONTACT, STUDY):
        for f in item_of(name)['fields']:
            assert f['class'] in CASCADES or f.get('fill') or (name, f['pointer']) in {
                (CONTACT, p) for p in ('/fixed_source_models/index_path', '/fixed_source_models/index_sha256')}, (name, f['pointer'])
            if f['class'] in ('doc-path', 'doc-sha256'): assert f['document'] in DECLARED['documents']
            if f['class'] == 'port-sha256':
                assert f['port_tree'] == 'T-e' and f['cascade_value'] == sha(blob(port_rev('T-e'), f['port_file']))
    assert {f['pointer']: f['class'] for f in item_of(INDEX)['fields']}['/training_source_code'] == 'source-map'
    assert driver.doc_path_value(PINS, STUDY) == 'docs/plans/m7-navigation-v4-pins/' + STUDY   # repo-relative, like the originals


def synthetic_s0d(tmp_path, *, differ=False):
    """A merged S0d chain entry over real-format seed files, plus an S0c entry."""
    root, tree = tmp_path/'tree/runs/S0d', tmp_path/'tree'
    outputs = {}
    for s in (10, 11, 12):
        seed = json.loads((S0D_EVIDENCE/f'seed-{s}/protocol.json').read_text())
        seed['model_inputs'] = {str(tree/Path(k).relative_to(TD_TREE)): v for k, v in seed['model_inputs'].items()}
        if differ and s == 12: seed['source_code']['trainer']['uv.lock'] = '0'*64
        for rel, value in ((f'seed-{s}/protocol.json', seed), (f'seed-{s}/report.json', {'seed': s})):
            path = root/rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
            outputs[rel] = {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    for rel in ('control/terminal.json', 'control/outer-supervisor/supervisor.json'):
        path = root/rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(rel)
        outputs[rel] = {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    s0c = tmp_path/'S0c/data'; s0c.mkdir(parents=True); (s0c/'data-manifest.json').write_text('{}')
    return {'S0c': {'producing_commit': 'c', 'worktree': '/w', 'output_root': str(s0c),
                    'outputs': {'data-manifest.json': {'sha256': sha(b'{}'), 'bytes': 2}}},
            'S0d': {'producing_commit': 'd'*40, 'worktree': str(tree), 'output_root': str(root), 'outputs': outputs,
                    'declared_values': ['a'*64]}}


def test_fill_derives_every_recovery_index_field_from_the_s0c_and_merged_s0d_chain(tmp_path):
    chain = synthetic_s0d(tmp_path)
    doc, original = placeholders(INDEX), json.loads((ROOT/item_of(INDEX)['original_path']).read_text())
    values = driver.fill_values(INDEX, item_of(INDEX), doc, original, chain, pins_dir=PINS)
    seed10 = json.loads((S0D_EVIDENCE/'seed-10/protocol.json').read_text())
    assert values['/training_source_code'] == seed10['source_code']
    assert list(values['/model_inputs'].values()) == list(seed10['model_inputs'].values())
    assert all(Path(k).is_relative_to(tmp_path/'tree') for k in values['/model_inputs'])
    assert values['/training_source_commit'] == 'd'*40 and values['/before_after_inventory_sha256'] == 'a'*64
    assert values['/producer_root'] == str(tmp_path/'tree') and values['/pairs/1/directory'] == 'runs/S0d/seed-11'
    assert values['/training_terminal/path'] == 'runs/S0d/control/terminal.json'
    assert values['/data_manifest/path'] == str(tmp_path/'S0c/data/data-manifest.json')
    for pointer, value in values.items(): driver.pointer_set(doc, pointer, value)
    driver.check_document_values(INDEX, doc, original, item_of(INDEX), chain, lambda other: None, PINS)
    tampered = copy.deepcopy(doc); tampered['training_source_code']['trainer']['uv.lock'] = '1'*64
    with pytest.raises(driver.Refusal):
        driver.check_document_values(INDEX, tampered, original, item_of(INDEX), chain, lambda other: None, PINS)


def test_fill_refuses_seed_protocols_that_differ_or_files_that_differ_from_their_record(tmp_path):
    original = json.loads((ROOT/item_of(INDEX)['original_path']).read_text())
    with pytest.raises(driver.Refusal, match='differs across'):
        driver.fill_values(INDEX, item_of(INDEX), placeholders(INDEX), original, synthetic_s0d(tmp_path/'a', differ=True), pins_dir=PINS)
    chain = synthetic_s0d(tmp_path/'b')
    (Path(chain['S0d']['output_root'])/'seed-11/protocol.json').write_text('{}')
    with pytest.raises(driver.Refusal, match='differs from its pin record'):
        driver.fill_values(INDEX, item_of(INDEX), placeholders(INDEX), original, chain, pins_dir=PINS)


def test_cascades_refuse_a_referenced_copy_that_still_holds_placeholders_or_port_bytes_that_differ(tmp_path):
    pins = tmp_path/'pins'; pins.mkdir()
    (pins/'declared-fields.json').write_bytes((PINS/'declared-fields.json').read_bytes())
    (pins/INDEX).write_text(json.dumps(placeholders(INDEX), indent=2) + '\n')
    tree = tmp_path/'tree'
    for name in (INDEX, CONTACT, STUDY, driver.RECOVERY_LEARNING):
        target = tree/item_of(name)['original_path']; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/item_of(name)['original_path']).read_bytes())
    with pytest.raises(driver.Refusal, match='PENDING'):
        driver.referenced_copy_sha(pins, DECLARED, tree, INDEX)
    port = next(f for f in item_of(STUDY)['fields'] if f['class'] == 'port-sha256')
    (tree/port['port_file']).parent.mkdir(parents=True, exist_ok=True); (tree/port['port_file']).write_text('not the port')
    # Port-byte pins are checked against the tree the field names (T-e), not the stage worktree given.
    values = driver.fill_values(STUDY, item_of(STUDY), placeholders(STUDY), {}, {}, pins_dir=PINS, worktree=tree,
                                doc_sha=lambda other: 'x'*64)
    assert values[port['pointer']] == port['cascade_value'] == sha(blob(port_rev('T-e'), port['port_file']))
    for changed, match in (({**port, 'cascade_value': '0'*64}, 'not the declared port bytes'), ({**port, 'port_tree': 'T-x'}, 'T-x')):
        with pytest.raises(driver.Refusal, match=match):
            driver.fill_values(STUDY, {**item_of(STUDY), 'fields': [changed]}, placeholders(STUDY), {}, {}, pins_dir=PINS, worktree=tree)


def test_contact_collector_port_pin_is_accepted_with_a_t_f_worktree_whose_v1_collector_is_unported(tmp_path):
    """S0f passes T-f (unported collect_male_navigation.py d0decc66) while contact-v2 pins the T-e port bytes."""
    field = next(f for f in item_of(CONTACT)['fields'] if f['pointer'] == '/prior_version/collector_sha256')
    tree = tmp_path/'t-f'; (tree/'scripts').mkdir(parents=True)
    unported = blob(SPEC['trees']['T-f']['branch'], 'scripts/collect_male_navigation.py')
    (tree/'scripts/collect_male_navigation.py').write_bytes(unported)
    assert sha(unported) != field['cascade_value']                                   # the bytes differ by design
    contact = json.loads((PINS/CONTACT).read_bytes())
    original = json.loads((ROOT/item_of(CONTACT)['original_path']).read_text())
    driver.check_document_values(CONTACT, contact, original, {**item_of(CONTACT), 'fields': [field]}, {}, lambda other: None, PINS,
                                 worktree=tree)
    forged = copy.deepcopy(contact); forged['prior_version']['collector_sha256'] = sha(unported)
    with pytest.raises(driver.Refusal):
        driver.check_document_values(CONTACT, forged, original, {**item_of(CONTACT), 'fields': [field]}, {}, lambda other: None,
                                     PINS, worktree=tree)


TF_TREE = Path('/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f')


@pytest.mark.skipif(not all(p.exists() for p in S0D_RECORDS) or not TF_TREE.exists(), reason='S0d evidence host only')
def test_s0f_dry_loads_the_contact_v2_copy_against_the_real_t_f_worktree_on_the_evidence_host():
    stages = driver.port_stages(driver.STAGES, driver.load_ports())
    chain = driver.previous_chain([json.loads(p.read_bytes()) for p in S0D_RECORDS], 'S0e', stages,
                                  protocol_sha256=driver.PROTOCOL_SHA256)
    declarations = driver.load_declarations(PINS, driver.PROTOCOL_SHA256)
    assert CONTACT in stages['S0f']['documents']
    documents = driver.load_pin_documents({'documents': [CONTACT]}, PINS, declarations, TF_TREE, chain)
    assert documents[CONTACT]['sha256'] == sha((PINS/CONTACT).read_bytes())


def test_tracked_s0e_copies_hold_the_published_s0c_s0d_values_and_cascades():
    values = json.loads((S0D_EVIDENCE/'control-recovery-index-values.json').read_text())
    seed10 = json.loads((S0D_EVIDENCE/'seed-10/protocol.json').read_text())
    index = json.loads((PINS/INDEX).read_bytes())
    for key in ('producer_root', 'training_source_commit', 'training_terminal', 'training_supervisor', 'before_after_inventory_sha256'):
        assert index[key] == values[key], key
    assert [{k: p[k] for k in ('directory', 'report_sha256', 'training_seed')} for p in index['pairs']] == values['pairs']
    assert index['training_source_code'] == seed10['source_code'] and index['model_inputs'] == seed10['model_inputs']
    s0c = json.loads((ROOT/'docs/reports/male-v4-s0c/pin-record.json').read_text())
    assert index['data_manifest'] == {'path': str(Path(s0c['output_root'])/'data-manifest.json'),
                                      'sha256': s0c['outputs']['data-manifest.json']['sha256']}
    contact, study = json.loads((PINS/CONTACT).read_bytes()), json.loads((PINS/STUDY).read_bytes())
    assert contact['fixed_source_models']['index_sha256'] == sha((PINS/INDEX).read_bytes())
    assert contact['fixed_source_models']['index_path'] == 'docs/plans/m7-navigation-v4-pins/' + INDEX
    assert contact['fixed_source_models']['producer_root'] == values['producer_root']
    assert contact['fixed_source_models']['pair_report_sha256'] == {str(p['training_seed']): p['report_sha256'] for p in values['pairs']}
    assert contact['data']['old_manifest_sha256'] == s0c['outputs']['data-manifest.json']['sha256']
    assert contact['prior_version']['protocol_sha256'] == sha((PINS/STUDY).read_bytes())
    assert contact['prior_version']['collector_sha256'] == sha(blob(port_rev('T-e'), 'scripts/collect_male_navigation.py'))
    current = study['current_reusable_source_sha256']
    assert current['data/manifests/male-recovery-research-development-v1.json'] == sha((PINS/INDEX).read_bytes())
    assert current['docs/plans/m7-recovery-learning-protocol.json'] == sha((PINS/driver.RECOVERY_LEARNING).read_bytes())
    assert current['src/palimpsest/male_recovery_research.py'] == sha(blob(port_rev('T-e'), 'src/palimpsest/male_recovery_research.py'))
    for name in (INDEX, CONTACT, STUDY):
        original = (ROOT/item_of(name)['original_path']).read_bytes()
        driver.check_pin_document(original, (PINS/name).read_bytes(), item_of(name), consumer=True)   # no PENDING left


@pytest.mark.skipif(not all(p.exists() for p in S0D_RECORDS) or not TE_TREE.exists(), reason='S0d evidence host only')
def test_tracked_s0e_copies_trace_to_the_live_merged_s0d_chain_on_the_evidence_host():
    stages = driver.port_stages(driver.STAGES, driver.load_ports())
    chain = driver.previous_chain([json.loads(p.read_bytes()) for p in S0D_RECORDS], 'S0e', stages,
                                  protocol_sha256=driver.PROTOCOL_SHA256)
    declarations = driver.load_declarations(PINS, driver.PROTOCOL_SHA256)
    spec = stages['S0e']
    documents = driver.load_pin_documents(spec, PINS, declarations, TE_TREE, chain)   # every S0e copy validated and traced
    assert set(documents) == {CONTACT, INDEX, driver.RECOVERY_LEARNING, STUDY}
