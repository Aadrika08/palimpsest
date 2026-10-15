"""Authored admission metadata only; no accepted qualification or model execution."""
from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys
import time

import pytest

from palimpsest import assets, memory
from scripts import memory_family_compact_v4 as compact


def module():
    name = 'scripts.memory_condition_replay_admission_v1'
    assert importlib.util.find_spec(name) is not None, 'Qualified replay admission is missing'
    return importlib.import_module(name)


def descriptor(path, payload=b'authored metadata'):
    return {'path': path, 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def receipt():
    """Prospective shape, never an accepted actual qualification receipt."""
    source_rows = [{key: row[key] for key in ('path', 'size_bytes', 'sha256')}
                   for row in compact.PROTOCOL['behavior_sources']]
    source_rows += copy.deepcopy(compact.PROTOCOL['cell_replay']['upstream_sources'])
    paths = {row['path']: row for row in source_rows}
    for path in ('docs/plans/memory-family-compact-evidence-v4-protocol.json',
                 'scripts/memory_condition_replay_admission_v1.py',
                 'scripts/memory_family_condition_seal_v4.py',
                 'docs/plans/memory-condition-seal-v1-protocol.json',
                 'docs/plans/memory-condition-seal-v1.md'):
        paths[path] = descriptor(path)
    paths['docs/plans/memory-family-compact-evidence-v4-protocol.json'] = descriptor(
        'docs/plans/memory-family-compact-evidence-v4-protocol.json', compact.PROTOCOL_BYTES)
    edge = 'graph/connections_princeton.csv'
    checkpoint = 'connectome_rnn_dagger_princeton_full_vision.pt'
    asset_paths = [edge, checkpoint, *('graph/' + name for name in assets.MAPPING_NAMES)]
    python = Path(sys.executable).resolve()
    return {
        'schema': 'memory-condition-cell-qualification-admission-v1',
        'status': 'accepted', 'scope': 'three-historical-traces-full-model-encoded-cell-only',
        'protocol_sha256': compact.PROTOCOL_SHA256,
        'replay_consumer_sha256': paths['scripts/memory_family_cell_replay_v4.py']['sha256'],
        'inputs': {
            'sources': {'root': str(compact.ROOT), 'files': sorted(paths.values(), key=lambda row: row['path'])},
            'assets': {'root': '/authored-model-assets', 'files': [descriptor(p) for p in sorted(asset_paths)]},
            'runtime': {'root': str(python.parent), 'files': [descriptor(python.name)]},
        },
        'model': {'edge': edge, 'checkpoint': checkpoint, 'seed': 400},
        'runtime_identity': {'python': [3, 11, 15], 'numpy': '2.2.5', 'torch': '2.9.0',
                             'torch_profile': {'authored': 'not measured'}},
        'model_provenance': {'authored': 'not a real model'},
        'controller_tensors': {'authored': 'not real tensors'},
        'audit': {role: descriptor(role + '.json') for role in ('freeze', 'terminal', 'outcome_audit')},
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }


def test_unpinned_receipt_refuses_before_any_open_or_numerical_import(monkeypatch):
    m = module()
    assert m.TRUSTED_QUALIFICATION_PINS == ()
    def forbidden(*args, **kwargs):
        pytest.fail('Unpinned admission attempted protected access')
    monkeypatch.setattr(m, 'HeldReplayFiles', forbidden)
    before = set(sys.modules)
    with pytest.raises(PermissionError):
        with m.qualified_replay('/does-not-exist', descriptor('forged.json'),
                                deadline=time.monotonic() + 30):
            pytest.fail('Unpinned admission yielded')
    assert not ({'numpy', 'torch', 'palimpsest.flynn'} & (set(sys.modules) - before))


def test_pure_pin_check_refuses_forged_status_without_access(monkeypatch):
    m = module()
    monkeypatch.setattr(m, 'HeldReplayFiles', lambda *a, **k: pytest.fail('Pin check accessed files'))
    with pytest.raises(PermissionError): m.require_qualification_pin(descriptor('forged.json'))


def test_repository_trust_anchor_cannot_be_inside_its_receipts_source_closure():
    m = module()
    value = receipt()
    value['inputs']['sources']['files'].append(descriptor(
        'scripts/memory_condition_qualification_pins_v1.py'))
    value['inputs']['sources']['files'].sort(key=lambda row: row['path'])
    with pytest.raises(ValueError, match='trust anchor'):
        m._validate_receipt(value)


def test_repository_anchor_can_rotate_without_changing_self_authenticated_helper(monkeypatch):
    """An authored private anchor replacement checks graph separation, never real qualification."""
    m = module()
    anchor_name = 'scripts.memory_condition_qualification_pins_v1'
    assert importlib.util.find_spec(anchor_name) is not None, 'Independent trust anchor is missing'
    anchor = importlib.import_module(anchor_name)
    helper_bytes = Path(m.__file__).read_bytes()
    pin = descriptor('authored-only-qualification.json')
    try:
        with monkeypatch.context() as patch:
            patch.setattr(anchor, 'TRUSTED_QUALIFICATION_PINS',
                          (tuple(pin[key] for key in ('path', 'size_bytes', 'sha256')),))
            importlib.reload(m)
            m.require_qualification_pin(pin)
            m._validate_receipt(receipt())
            assert Path(m.__file__).read_bytes() == helper_bytes
    finally:
        importlib.reload(m)
    with pytest.raises(PermissionError): m.require_qualification_pin(pin)


def test_environment_cannot_replace_repository_trust_anchor(monkeypatch):
    m = module()
    monkeypatch.setenv('MEMORY_CONDITION_QUALIFICATION_PINS', 'caller-controlled.json')
    monkeypatch.setenv('TRUSTED_QUALIFICATION_PINS', 'caller-controlled.json')
    monkeypatch.setattr(m, 'HeldReplayFiles', lambda *a, **k: pytest.fail('Environment override accessed input'))
    with pytest.raises(PermissionError):
        with m.qualified_replay('/absent', descriptor('caller-controlled.json'), deadline=time.monotonic()+30):
            pytest.fail('Environment supplied an authority grant')


@pytest.mark.parametrize('bad', [None, {}, {'path': '../escape', 'size_bytes': 1, 'sha256': 'a'*64},
                                {'path': 'x', 'size_bytes': True, 'sha256': 'a'*64},
                                {'path': 'x', 'size_bytes': 1024**2+1, 'sha256': 'a'*64}])
def test_invalid_receipt_descriptor_refuses_without_file_access(monkeypatch, bad):
    m = module()
    monkeypatch.setattr(m, 'HeldReplayFiles', lambda *a, **k: pytest.fail('Invalid descriptor opened input'))
    with pytest.raises(ValueError):
        with m.qualified_replay('/absent', bad, deadline=time.monotonic() + 30):
            pytest.fail('Invalid descriptor yielded')


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), -1, None])
def test_invalid_deadline_refuses_before_access(monkeypatch, value):
    m = module()
    monkeypatch.setattr(m, 'HeldReplayFiles', lambda *a, **k: pytest.fail('Invalid deadline opened input'))
    with pytest.raises((ValueError, TimeoutError)):
        with m.qualified_replay('/absent', descriptor('x'), deadline=value):
            pytest.fail('Invalid deadline yielded')


def test_overlong_deadline_refuses():
    m = module()
    with pytest.raises(ValueError):
        with m.qualified_replay('/absent', descriptor('x'), deadline=time.monotonic()+301):
            pytest.fail('Overlong deadline yielded')


def test_prospective_shape_validation_does_not_make_an_admission():
    m = module()
    value = receipt()
    m._validate_receipt(value)
    with pytest.raises(PermissionError):
        with m.qualified_replay('/absent', descriptor('accepted.json'), deadline=time.monotonic()+30):
            pytest.fail('Shape validation granted replay')


@pytest.mark.parametrize('defect', [
    'unknown', 'status', 'scope', 'protocol', 'consumer', 'claims', 'model-seed',
    'runtime-unknown', 'runtime-python', 'runtime-numpy', 'runtime-torch',
    'sources-root', 'source-omission', 'source-rebind', 'source-duplicate',
    'assets-omission', 'assets-extra', 'assets-unordered', 'model-edge',
    'runtime-omission', 'audit-alias', 'audit-extra', 'audit-large',
    'provenance-type', 'tensors-type',
])
def test_prospective_receipt_rejects_incomplete_or_changed_identity(defect):
    m = module()
    value = receipt()
    if defect == 'unknown': value['unreviewed'] = True
    elif defect == 'status': value['status'] = 'passed'
    elif defect == 'scope': value['scope'] = 'full-simulation'
    elif defect == 'protocol': value['protocol_sha256'] = '0' * 64
    elif defect == 'consumer': value['replay_consumer_sha256'] = '0' * 64
    elif defect == 'claims': value['claims']['cell_replay_verified'] = True
    elif defect == 'model-seed': value['model']['seed'] = True
    elif defect == 'runtime-unknown': value['runtime_identity']['cuda'] = False
    elif defect == 'runtime-python': value['runtime_identity']['python'] = [3, 11, True]
    elif defect == 'runtime-numpy': value['runtime_identity']['numpy'] = '2.3.0'
    elif defect == 'runtime-torch': value['runtime_identity']['torch'] = '2.8.0'
    elif defect == 'sources-root': value['inputs']['sources']['root'] = '/other-checkout'
    elif defect == 'source-omission': value['inputs']['sources']['files'].pop()
    elif defect == 'source-rebind':
        next(row for row in value['inputs']['sources']['files']
             if row['path'] == 'scripts/memory_family_cell_replay_v4.py')['sha256'] = '0'*64
    elif defect == 'source-duplicate': value['inputs']['sources']['files'] *= 2
    elif defect == 'assets-omission': value['inputs']['assets']['files'].pop()
    elif defect == 'assets-extra': value['inputs']['assets']['files'].append(descriptor('unbound.csv'))
    elif defect == 'assets-unordered': value['inputs']['assets']['files'].reverse()
    elif defect == 'model-edge': value['model']['edge'] = '../connections.csv'
    elif defect == 'runtime-omission': value['inputs']['runtime']['files'] = []
    elif defect == 'audit-alias': value['audit']['terminal'] = value['audit']['freeze']
    elif defect == 'audit-extra': value['audit']['operator'] = descriptor('operator.json')
    elif defect == 'audit-large': value['audit']['terminal']['size_bytes'] = 1024**2+1
    elif defect == 'provenance-type': value['model_provenance'] = []
    elif defect == 'tensors-type': value['controller_tensors'] = []
    with pytest.raises(ValueError): m._validate_receipt(value)


@pytest.mark.parametrize('field', ['path', 'size_bytes', 'sha256'])
def test_exact_pin_does_not_authorize_a_changed_descriptor(monkeypatch, field):
    m = module()
    original = descriptor('reviewed.json')
    monkeypatch.setattr(m, 'TRUSTED_QUALIFICATION_PINS',
                        (tuple(original[key] for key in ('path', 'size_bytes', 'sha256')),))
    changed = copy.deepcopy(original)
    changed[field] = {'path': 'other.json', 'size_bytes': 18, 'sha256': '0'*64}[field]
    with pytest.raises(PermissionError): m.require_qualification_pin(changed)


@pytest.fixture
def orchestration(tmp_path, monkeypatch):
    """Private seams bypass qualification/model admission; only authored FD custody is real."""
    m = module()
    value = receipt()
    for role in ('sources', 'assets', 'runtime'):
        directory = tmp_path / role
        directory.mkdir()
        paths = ([*m.EXTENSION_SOURCES, m.EXTENSION_PATH] if role == 'sources'
                 else [row['path'] for row in value['inputs'][role]['files']])
        values = []
        for path in paths:
            target = directory / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'authored test input; never a model or interpreter')
            values.append(descriptor(path, target.read_bytes()))
        if role == 'sources':
            extension = {'schema': 'memory-condition-seal-v1-protocol',
                         'base_protocol_sha256': compact.PROTOCOL_SHA256,
                         'claims': copy.deepcopy(compact.PROTOCOL['claims']),
                         'source_pins': sorted([row for row in values if row['path'] != m.EXTENSION_PATH],
                                               key=lambda row: row['path'])}
            payload = memory.canonical_bytes(extension)
            (directory / m.EXTENSION_PATH).write_bytes(payload)
            values = [descriptor(m.EXTENSION_PATH, payload) if row['path'] == m.EXTENSION_PATH else row
                      for row in values]
        value['inputs'][role] = {'root': str(directory), 'files': sorted(values, key=lambda row: row['path'])}
    for row in value['audit'].values():
        payload = b'authored audit, not actual qualification'
        (tmp_path / row['path']).write_bytes(payload)
        row.update(descriptor(row['path'], payload))
    payload = memory.canonical_bytes(value)
    (tmp_path / 'receipt.json').write_bytes(payload)
    pin = descriptor('receipt.json', payload)
    monkeypatch.setattr(m, 'TRUSTED_QUALIFICATION_PINS',
                        (tuple(pin[key] for key in ('path', 'size_bytes', 'sha256')),))
    # A positive orchestration fixture cannot claim to validate a real model, source closure or runtime.
    monkeypatch.setattr(m, '_validate_receipt', lambda value: None)
    policy = object()
    monkeypatch.setattr(m, '_load_policy', lambda receipt, holders: policy)
    monkeypatch.setattr(m, '_check_policy', lambda policy, receipt: None)
    return m, tmp_path, pin, policy


def test_authored_orchestration_keeps_descriptors_immutable_and_expires_session(orchestration):
    m, root, pin, policy = orchestration
    original = copy.deepcopy(pin)
    with m.qualified_replay(root, pin, deadline=time.monotonic()+30) as session:
        pin['sha256'] = '0'*64
        exported = session.descriptor
        exported['sha256'] = '1'*64
        assert session.descriptor == original
        assert session.policy is policy
        session.recheck()
    with pytest.raises(RuntimeError): session.recheck()
    with pytest.raises(RuntimeError): _ = session.policy


def test_authored_orchestration_snapshots_descriptor_before_pin_check(orchestration, monkeypatch):
    m, root, pin, _ = orchestration
    original = copy.deepcopy(pin)
    check = m.require_qualification_pin
    def mutate_caller_after_check(checked):
        check(checked)
        pin['sha256'] = '0'*64
    monkeypatch.setattr(m, 'require_qualification_pin', mutate_caller_after_check)
    with m.qualified_replay(root, pin, deadline=time.monotonic()+30) as session:
        assert session.descriptor == original


@pytest.mark.parametrize('part', ['assets', 'sources', 'runtime', 'audit'])
def test_authored_orchestration_detects_late_held_file_drift(orchestration, part):
    m, root, pin, _ = orchestration
    with pytest.raises((ValueError, RuntimeError)):
        with m.qualified_replay(root, pin, deadline=time.monotonic()+30) as session:
            target = (root / 'terminal.json' if part == 'audit' else next(
                path for path in (root / part).rglob('*') if path.is_file()))
            target.write_bytes(b'changed authored input')
            try:
                session.recheck()
            except (ValueError, RuntimeError) as first:
                with pytest.raises(type(first)) as second: session.recheck()
                assert second.value is first


def test_authored_orchestration_preserves_body_error_when_teardown_also_fails(orchestration, monkeypatch):
    m, root, pin, _ = orchestration
    original_exit = m.HeldReplayFiles.__exit__
    def broken_exit(self, *args):
        original_exit(self, *args)
        raise OSError('authored descriptor close failure')
    monkeypatch.setattr(m.HeldReplayFiles, '__exit__', broken_exit)
    first = RuntimeError('authored body failure')
    with pytest.raises(RuntimeError) as caught:
        with m.qualified_replay(root, pin, deadline=time.monotonic()+30):
            raise first
    assert caught.value is first


def test_authored_orchestration_does_not_hide_teardown_failure(orchestration, monkeypatch):
    m, root, pin, _ = orchestration
    original_exit = m.HeldReplayFiles.__exit__
    def broken_exit(self, *args):
        original_exit(self, *args)
        raise OSError(self.root.name + ' authored descriptor close failure')
    monkeypatch.setattr(m.HeldReplayFiles, '__exit__', broken_exit)
    with pytest.raises(OSError, match='^runtime authored descriptor close failure$'):
        with m.qualified_replay(root, pin, deadline=time.monotonic()+30):
            pass
