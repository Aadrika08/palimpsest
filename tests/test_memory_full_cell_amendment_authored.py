"""Current validator checks on authored metadata in an isolated fake repository.

No real historical freeze, registry, checkpoint, model or runtime is read. Only
ROOT and the two prior-evidence trust anchors are patched, within each test;
production source and committed acceptance policies remain untouched. Passing
these fixtures grants no qualification, actual amendment approval or execution.
"""
import copy
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from scripts import qualify_memory_full_cell_v4 as m


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(m._canonical(value))
    return path.read_bytes()


def _descriptor(root, relative):
    payload = (root / relative).read_bytes()
    return {'path': relative, 'size_bytes': len(payload), 'sha256': _digest(payload)}


@pytest.fixture
def authored(tmp_path, monkeypatch):
    root = tmp_path / 'authored-repository'
    root.mkdir()
    for relative in m.SOURCE_FIXED:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'Authored source-roster stand-in; never imported.\n')
    for relative in ('src/palimpsest/fixture.py', 'scripts/fixture.py',
                     'upstream/fly-gym/fixture.py', 'upstream/fly-gym/fixture.xml'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'# Authored inert source fixture\n')
    monkeypatch.setattr(m, 'ROOT', root)
    source_rows = [_descriptor(root, relative) for relative in m._source_roster(root)]
    metadata = 'docs/authored-metadata.json'
    _save(root / metadata, {'authored': True, 'qualification_claims': []})
    original = {
        'schema': 'memory-full-cell-qualification-v4',
        'repo_root': str(root), 'run_ids': list(m.RUNS),
        'positive_cells': 737, 'max_cells': 1470, 'model_seed': 400,
        'native_owners': 0, 'physics_steps': 0, 'attempts': 1,
        'claims': {'family_admission': False, 'pruning_authorized': False,
                   'qualification_claims': []},
        'inputs': {
            'sources': {'root': str(root), 'files': source_rows},
            'metadata': {'root': str(root), 'files': [_descriptor(root, metadata)]},
            # These paths deliberately do not exist. _freeze is metadata-only.
            'raw': {'root': str(tmp_path / 'unopened-raw'),
                    'files': [{'path': 'authored.json', 'size_bytes': 3, 'sha256': 'a' * 64}]},
            'assets': {'root': str(tmp_path / 'unopened-assets'),
                       'files': [{'path': 'authored.bin', 'size_bytes': 3, 'sha256': 'b' * 64}]},
            'runtime': {'root': str(tmp_path / 'unopened-runtime'),
                        'files': [{'path': 'python3.11', 'size_bytes': None,
                                   'max_bytes': 1024**2, 'sha256': 'c' * 64}]},
        },
        'environment': copy.deepcopy(m.ENVIRONMENT),
        'output': str(root / 'runs/memory-full-cell-qualification-v4-attempt-01'),
        'model_edge': ('graph-49d19491c1df4b8f02af0e285b71dc171f47488a93ee5b91be8ee4e280bee9f1/'
                       'drosophila adult connectome/connections_princeton.csv'),
        'model_checkpoint': 'connectome_rnn_dagger_princeton_full_vision.pt',
        'python_executable': m.PYTHON,  # String metadata only; never invoked.
        'limits': copy.deepcopy(m.LIMITS),
        'supervisor': {'path': '/usr/bin/timeout', 'sha256': 'd' * 64,
                       'argv': ['--signal=TERM', '--kill-after=10s', '650s']},
    }
    prior = root / m.PRIOR
    prior.mkdir(parents=True)
    _save(prior / 'diagnostic.json', {'authored': True, 'worker_started': False,
                                     'model_inference_calls': 0})
    freeze_raw = _save(prior / 'execution-freeze.json', original)
    index = {
        'schema': 'authored-consumed-prior-failure-fixture',
        'status': 'failed-consumed-before-numerical-worker',
        'worker_started': False, 'model_inference_calls': 0,
        'files': [{**_descriptor(prior, 'diagnostic.json')}],
    }
    index_raw = _save(prior / 'index.json', index)
    monkeypatch.setattr(m, 'PRIOR_INDEX_SHA', _digest(index_raw))
    monkeypatch.setattr(m, 'PRIOR_FREEZE_SHA', _digest(freeze_raw))
    candidate = copy.deepcopy(original)
    candidate.update(schema=m.AMENDMENT, attempt_number=2,
                     output=str(root / 'runs/memory-full-cell-qualification-v4-attempt-02'),
                     prior_attempt=_descriptor(root, m.PRIOR + 'index.json'))
    candidate['inputs']['runtime']['files'] = [
        {'path': 'python3.11', 'size_bytes': 21662864, 'sha256': m.RUNTIME_SHA}]
    additions = [_descriptor(root, m.PRIOR + name)
                 for name in ('index.json', 'execution-freeze.json', 'diagnostic.json')]
    candidate['inputs']['metadata']['files'] = sorted(
        candidate['inputs']['metadata']['files'] + additions, key=lambda row: row['path'])
    serial = 0

    def load(value):
        nonlocal serial
        serial += 1
        path = tmp_path / f'authored-freeze-{serial}.json'
        payload = _save(path, value)
        return m._freeze(path, _digest(payload))

    # Every negative starts from a genuinely accepted baseline, not an unrelated
    # root/cache refusal. No validator or source-roster function is patched.
    native_modules_before = frozenset({'torch', 'mujoco'} & set(sys.modules))
    assert load(candidate) == candidate
    return SimpleNamespace(root=root, candidate=candidate, load=load,
                           index_raw=index_raw, freeze_raw=freeze_raw,
                           native_modules_before=native_modules_before)


def test_authored_baseline_accepts_without_opening_any_raw_asset_or_runtime(authored):
    candidate = authored.load(authored.candidate)
    assert candidate['attempt_number'] == 2
    assert candidate['claims'] == {'family_admission': False, 'pruning_authorized': False,
                                   'qualification_claims': []}
    assert candidate['native_owners'] == candidate['physics_steps'] == 0
    assert candidate['inputs']['runtime']['files'] == [
        {'path': 'python3.11', 'size_bytes': 21662864, 'sha256': m.RUNTIME_SHA}]
    for role in ('raw', 'assets', 'runtime'):
        assert not Path(candidate['inputs'][role]['root']).exists()
    assert not Path(candidate['output']).exists()
    assert (authored.root / m.PRIOR / 'index.json').read_bytes() == authored.index_raw
    assert (authored.root / m.PRIOR / 'execution-freeze.json').read_bytes() == authored.freeze_raw
    # Other source tests may have imported a framework earlier in this process;
    # this metadata fixture must add no native/model module itself.
    assert frozenset({'torch', 'mujoco'} & set(sys.modules)) == authored.native_modules_before


@pytest.mark.parametrize(('defect', 'message'), [
    ('runtime-unknown', 'Amendment exact-size runtime binding differs'),
    ('runtime-size', 'Amendment exact-size runtime binding differs'),
    ('runtime-hash', 'Amendment exact-size runtime binding differs'),
    ('raw-root', 'Amendment changes original input role: raw'),
    ('asset-hash', 'Amendment changes original input role: assets'),
    ('missing-prior', 'Amendment prior evidence metadata roster differs'),
    ('prior-hash', 'Amendment prior failure or attempt number differs'),
    ('prior-size-alias', 'Amendment prior failure or attempt number differs'),
    ('attempt-alias', 'Amendment prior failure or attempt number differs'),
    ('attempt-three', 'Amendment prior failure or attempt number differs'),
    ('limits', 'Execution freeze invocation or limits differ'),
    ('source-extra', 'Amendment execution source namespace differs'),
])
def test_authored_amendment_rejects_the_intended_changed_boundary(authored, defect, message):
    candidate = copy.deepcopy(authored.candidate)
    if defect == 'runtime-unknown':
        candidate['inputs']['runtime']['files'][0].update(size_bytes=None, max_bytes=1024**2)
    elif defect == 'runtime-size':
        candidate['inputs']['runtime']['files'][0]['size_bytes'] += 1
    elif defect == 'runtime-hash':
        candidate['inputs']['runtime']['files'][0]['sha256'] = '0' * 64
    elif defect == 'raw-root':
        candidate['inputs']['raw']['root'] += '/replacement'
    elif defect == 'asset-hash':
        candidate['inputs']['assets']['files'][0]['sha256'] = '0' * 64
    elif defect == 'missing-prior':
        candidate['inputs']['metadata']['files'].remove(candidate['prior_attempt'])
    elif defect == 'prior-hash':
        candidate['prior_attempt']['sha256'] = '0' * 64
    elif defect == 'prior-size-alias':
        candidate['prior_attempt']['size_bytes'] = float(candidate['prior_attempt']['size_bytes'])
    elif defect == 'attempt-alias':
        candidate['attempt_number'] = 2.0
    elif defect == 'attempt-three':
        candidate['attempt_number'] = 3
    elif defect == 'limits':
        candidate['limits']['normal_seconds'] += 1
    else:
        candidate['inputs']['sources']['files'].append(
            {'path': 'extra.py', 'size_bytes': 0, 'sha256': '0' * 64})
    with pytest.raises(ValueError) as rejected:
        authored.load(candidate)
    assert str(rejected.value) == message


def test_authored_wrong_repository_root_still_refuses(authored):
    candidate = copy.deepcopy(authored.candidate)
    candidate['repo_root'] += '/different-root'
    with pytest.raises(ValueError, match='^Execution freeze scope differs$'):
        authored.load(candidate)


@pytest.mark.parametrize('directory', ['src/palimpsest', 'scripts', 'upstream/fly-gym'])
def test_authored_unbound_bytecode_still_refuses_without_deleting_it(authored, directory):
    cached = authored.root / directory / '__pycache__' / 'fixture.cpython-311.pyc'
    cached.parent.mkdir()
    cached.write_bytes(b'Authored inert bytecode sentinel; never imported')
    with pytest.raises(ValueError, match='^Qualification source has unbound bytecode$'):
        authored.load(authored.candidate)
    assert cached.read_bytes() == b'Authored inert bytecode sentinel; never imported'


@pytest.mark.parametrize('mode', ['parent', 'worker'])
def test_authored_command_confirmation_is_pure_without_repository_admission(mode):
    args = SimpleNamespace(freeze='authored-unused.json', freeze_sha256='a' * 64,
                           approved_amendment_sha256='a' * 64)
    command = m._execution_command({'schema': m.AMENDMENT}, args, mode)
    assert command[-1] == '--' + mode
    assert command[command.index('--approved-amendment-sha256') + 1] == args.freeze_sha256
