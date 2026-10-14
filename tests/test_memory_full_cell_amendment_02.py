"""Prospective amendment metadata and authored temporary runtime only; no actual invocation."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time

import pytest
from scripts import qualify_memory_full_cell_v4 as m
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles

PRIOR = 'docs/reports/memory-full-cell-qualification-v4-attempt-01-evidence/'
ORIGINAL_SHA = '9bba5a4a4fdd980ab2022d7ef0813aa4b2fa6a2c26c6ce86fead7110ad624c82'
RUNTIME_SHA = '572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'


def descriptor(path):
    raw = (m.ROOT / path).read_bytes()
    return {'path': path, 'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def candidate():
    f = json.loads((m.ROOT / (PRIOR + 'execution-freeze.json')).read_bytes())
    f['schema'] = 'memory-full-cell-qualification-v4-amendment-02'
    f['attempt_number'] = 2
    f['output'] = str(m.ROOT / 'runs/memory-full-cell-qualification-v4-attempt-02')
    f['prior_attempt'] = descriptor(PRIOR + 'index.json')
    f['inputs']['runtime']['files'] = [{'path': 'python3.11', 'size_bytes': 21662864, 'sha256': RUNTIME_SHA}]
    index = json.loads((m.ROOT / (PRIOR + 'index.json')).read_bytes())
    additions = [descriptor(PRIOR + path) for path in ('index.json', 'execution-freeze.json', *[r['path'] for r in index['files']])]
    f['inputs']['metadata']['files'] = sorted(f['inputs']['metadata']['files'] + additions, key=lambda r: r['path'])
    f['inputs']['sources']['files'] = [descriptor(path) for path in m._source_roster(m.ROOT)]
    return f


def load(tmp_path, f):
    raw = m._canonical(f)
    path = tmp_path / 'freeze.json'
    path.write_bytes(raw)
    return m._freeze(path, hashlib.sha256(raw).hexdigest())


def test_amendment_accepts_exact_runtime_size_and_preserved_prior_failure(tmp_path):
    f = load(tmp_path, candidate())
    assert f['attempt_number'] == 2
    assert f['inputs']['runtime']['files'][0]['size_bytes'] == 21662864
    assert 'max_bytes' not in f['inputs']['runtime']['files'][0]
    assert len(f['inputs']['metadata']['files']) == 13
    assert f['claims']['qualification_claims'] == []


@pytest.mark.parametrize('defect', ['runtime-unknown', 'runtime-size', 'runtime-hash', 'raw-root',
    'asset-hash', 'missing-prior', 'prior-hash', 'attempt-alias', 'attempt-three', 'limits', 'source-extra'])
def test_amendment_refuses_expanded_or_ambiguous_allocation(tmp_path, defect):
    f = candidate()
    if defect == 'runtime-unknown':
        f['inputs']['runtime']['files'][0].update(size_bytes=None, max_bytes=1024**2)
    elif defect == 'runtime-size': f['inputs']['runtime']['files'][0]['size_bytes'] += 1
    elif defect == 'runtime-hash': f['inputs']['runtime']['files'][0]['sha256'] = '0' * 64
    elif defect == 'raw-root': f['inputs']['raw']['root'] += '/replacement'
    elif defect == 'asset-hash': f['inputs']['assets']['files'][0]['sha256'] = '0' * 64
    elif defect == 'missing-prior': f['inputs']['metadata']['files'].pop()
    elif defect == 'prior-hash': f['prior_attempt']['sha256'] = '0' * 64
    elif defect == 'attempt-alias': f['attempt_number'] = 2.0
    elif defect == 'attempt-three': f['attempt_number'] = 3
    elif defect == 'limits': f['limits']['normal_seconds'] += 1
    else: f['inputs']['sources']['files'].append({'path': 'extra.py', 'size_bytes': 0, 'sha256': '0'*64})
    with pytest.raises(ValueError): load(tmp_path, f)


@pytest.mark.parametrize('confirmation', [None, '0' * 64])
def test_missing_or_different_confirmation_refuses_before_reservation(tmp_path, confirmation):
    f = candidate()
    raw = m._canonical(f)
    path = tmp_path / 'freeze.json'
    path.write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    argv = ['--freeze', str(path), '--freeze-sha256', sha]
    if confirmation is not None: argv += ['--approved-amendment-sha256', confirmation]
    output = Path(f['output'])
    assert not output.exists(), 'Actual amendment allocation must remain unused'
    with pytest.raises(ValueError, match='approval'):
        m.main(argv)
    assert not output.exists()


def test_confirmation_and_amendment_identity_propagate_to_parent_and_worker():
    assert hasattr(m, '_execution_command'), 'Amendment subprocess identity propagation is missing'
    f = candidate()
    args = SimpleNamespace(freeze='prospective.json', freeze_sha256='a'*64, approved_amendment_sha256='a'*64)
    for mode in ('parent', 'worker'):
        argv = m._execution_command(f, args, mode)
        assert argv[-1] == '--' + mode
        assert argv[argv.index('--approved-amendment-sha256')+1] == args.freeze_sha256


def test_large_known_runtime_uses_existing_cap_without_relaxing_unknown_metadata(tmp_path):
    path = tmp_path / 'runtime'
    with path.open('wb') as stream: stream.truncate(21662864)
    raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    fixed = {'path': path.name, 'size_bytes': 21662864, 'sha256': raw_sha}
    with HeldReplayFiles(tmp_path, [fixed], time.monotonic()+5) as held:
        assert held.path(path.name) == path
    unknown = {**fixed, 'size_bytes': None, 'max_bytes': 1024**2}
    with pytest.raises(ValueError):
        with HeldReplayFiles(tmp_path, [unknown], time.monotonic()+5): pass


def test_original_freeze_and_evidence_stay_byte_identical():
    assert hashlib.sha256((m.ROOT / 'docs/plans/memory-full-cell-qualification-v4-execution.json').read_bytes()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256((m.ROOT / (PRIOR+'execution-freeze.json')).read_bytes()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256((m.ROOT / (PRIOR+'index.json')).read_bytes()).hexdigest() == '27bac35a94811355fba6dd5fb93d37d9c4bd921de709647d44218e800c44eb82'
