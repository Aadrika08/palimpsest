"""Synthetic zero-owner allocation checks; no model, subprocess, or study runs."""
import builtins
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import uuid
from unittest.mock import patch

import pytest

from palimpsest import artifacts, memory
from scripts import memory_family_allocation_v3 as allocation
from test_memory_family_producer_v3 import (
    _build, _contract_inputs, _registration_file, _write,
)


ROOT = Path(__file__).parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-allocation-admission-v3-protocol.json'
UPSTREAM_IDENTITY = {
    'path': '/fixture/repo/upstream/fly-gym',
    'commit': '8d964599119b420de67ee259434d273651a1a76d',
    'files': 122,
    'bytes': 21_280_722,
    'inventory_sha256': 'ad06f7682f3c403f5b3b53d06e57594ffcb868997204796c6fba40b281b096bc',
}
ASSET_MODEL_IDENTITY = {
    'manifest': {'path': '/fixture/repo/model_manifests/flynn-full-vision.json',
                 'sha256': 'e319bb18e12110dbc096d62d3d6e9550c7b37434bf5e18e410c5410c21bb97e5'},
    'assets': {'fixture': True}, 'model': {'fixture': True},
    'prepared_graph': {'fixture': True},
}


def _search_manifest(tmp_path, *, historical=None, training=None):
    historical = historical or tmp_path / 'inventory-roots/history'
    training = training or tmp_path / 'inventory-roots/training'
    historical.mkdir(parents=True, exist_ok=True)
    training.mkdir(parents=True, exist_ok=True)
    manifest = _write(tmp_path / 'inventory/search.json', {
        'schema': 'memory-family-namespace-search-v3',
        'roots': [
            {'kind': 'historical', 'path': str(historical)},
            {'kind': 'training', 'path': str(training)},
        ],
    })
    return manifest, historical, training


def _admission_inputs(tmp_path, *, training_seed=10):
    search, historical, training = _search_manifest(tmp_path)
    _write(historical / 'history.json', {'id': 'retained-old-case'})
    _write(training / 'training.json', {
        'training_seed': training_seed, 'entity_id': 'trained-old-controller'})
    inventory = allocation.build_namespace_inventory(search)
    values = _contract_inputs(tmp_path)
    _write(values['inventory_path'], inventory['namespace'])
    registration = _build(values)
    registration_path = _registration_file(values, registration)
    return {
        'search': search, 'historical': historical, 'training': training,
        'inventory': inventory, 'values': values, 'registration': registration,
        'registration_path': registration_path,
    }


def _capacity(used=4096):
    additional = allocation.ALLOCATION_MAX_BYTES - used
    return {
        'filesystem_device': 7, 'used_bytes': used,
        'additional_bytes': additional,
        'allocation_max_bytes': allocation.ALLOCATION_MAX_BYTES,
        'free_bytes': additional + allocation.MIN_FREE_BYTES,
        'min_free_bytes': allocation.MIN_FREE_BYTES,
        'required_free_bytes': additional + allocation.MIN_FREE_BYTES,
        'shortfall_bytes': 0,
        'max_runs': 1448, 'max_snapshots_per_run': 2,
        'max_exports': 1592, 'max_entries': 131_072,
    }


def _admit(inputs, **patches):
    defaults = {
        '_capacity': _capacity(),
        '_upstream_identity': UPSTREAM_IDENTITY,
        '_asset_model_identity': ASSET_MODEL_IDENTITY,
    }
    defaults.update(patches)
    with patch.object(allocation, '_capacity', return_value=defaults['_capacity']), \
            patch.object(allocation, '_upstream_identity',
                         return_value=defaults['_upstream_identity']), \
            patch.object(allocation, '_asset_model_identity',
                         return_value=defaults['_asset_model_identity']):
        return allocation.admit(
            inputs['registration_path'], inputs['search'], ROOT,
            ROOT / 'fixture-assets')


def test_protocol_freezes_exact_capacity_arithmetic_and_is_canonical():
    payload = PROTOCOL_PATH.read_bytes()
    protocol = artifacts._json(payload)
    storage = protocol['storage']
    overhead = storage['non_recording']

    assert payload == memory.canonical_bytes(protocol) == allocation.PROTOCOL_BYTES
    assert storage['producer_subtotal_bytes'] == 627_836_977_152
    assert storage['non_recording_bytes'] == 6_710_886_400 == sum((
        overhead['owner_audits']['bytes'], overhead['case_closes']['bytes'],
        overhead['matrix_artifacts']['bytes'], overhead['namespace_inventory_bytes'],
        overhead['contract_artifacts']['bytes'], overhead['atomic_staging_bytes']))
    assert allocation.ALLOCATION_MAX_BYTES == 643_137_798_144
    assert allocation.MIN_FREE_BYTES == 2_147_483_648
    assert allocation.MINIMUM_CAPACITY_BYTES == 645_285_281_792
    assert protocol['population']['max_runs'] == 1448
    assert storage['max_entries'] == 131_072


def test_inventory_collects_all_bounded_strings_uuids_paths_and_training_seeds(tmp_path):
    search, historical, training = _search_manifest(tmp_path)
    inline_run = uuid.UUID(int=71).hex
    path_run = uuid.UUID(int=72).hex
    history = _write(historical / 'history.json', {
        'run_id': inline_run,
        'case': {'id': 'old-case', 'nested': ['old-subject']},
    })
    events = historical / 'events.jsonl'
    events.write_bytes(memory.canonical_bytes({'subject_id': 'event-subject'}) + b'\n')
    path_entry = historical / path_run / 'raw.bin'
    path_entry.parent.mkdir()
    path_entry.write_bytes(b'raw')
    training_file = _write(training / 'training.json', {
        'training_seed': 10, 'rewiring_seeds': [11, 12],
        'entity_id': 'trained-agent',
    })

    result = allocation.build_namespace_inventory(search)

    assert result['namespace'] == {
        'schema': 'memory-family-namespace-inventory-v3',
        'historical_run_ids': [inline_run, path_run],
        'historical_authored_ids': sorted([
            'events.jsonl', 'event-subject', 'history.json', 'old-case',
            'old-subject', 'raw.bin', 'trained-agent', 'training.json',
        ]),
    }
    assert result['search']['training_seeds'] == [10, 11, 12]
    assert result['search']['training_seeds_sha256'] == memory.sha256([10, 11, 12])
    roots = result['search']['roots']
    assert [(row['kind'], row['entries'], row['files'], row['bytes']) for row in roots] == [
        ('historical', 4, 3,
         history.stat().st_size + events.stat().st_size + path_entry.stat().st_size),
        ('training', 1, 1, training_file.stat().st_size),
    ]
    assert result['search']['searched_roots_sha256'] == memory.sha256(roots)
    assert result == allocation.build_namespace_inventory(search)


@pytest.mark.parametrize('defect', [
    'malformed-json', 'oversized-jsonl-line', 'symlink', 'special',
    'overlap', 'duplicate', 'entry-limit', 'byte-limit', 'held-out',
])
def test_inventory_rejects_incomplete_or_unsafe_searches(tmp_path, defect):
    search, historical, training = _search_manifest(tmp_path)
    limits = copy.deepcopy(allocation.INVENTORY_LIMITS)
    if defect == 'malformed-json':
        (historical / 'bad.json').write_text('{')
    elif defect == 'oversized-jsonl-line':
        limits['max_jsonl_line_bytes'] = 8
        (historical / 'events.jsonl').write_bytes(b'{"id":"too-long"}\n')
    elif defect == 'symlink':
        (historical / 'alias').symlink_to(training, target_is_directory=True)
    elif defect == 'special':
        os.mkfifo(historical / 'fifo')
    elif defect == 'overlap':
        nested = historical / 'nested'
        nested.mkdir()
        search = _write(tmp_path / 'inventory/overlap.json', {
            'schema': 'memory-family-namespace-search-v3',
            'roots': [{'kind': 'historical', 'path': str(historical)},
                      {'kind': 'training', 'path': str(nested)}],
        })
    elif defect == 'duplicate':
        search = _write(tmp_path / 'inventory/duplicate.json', {
            'schema': 'memory-family-namespace-search-v3',
            'roots': [{'kind': 'historical', 'path': str(historical)},
                      {'kind': 'training', 'path': str(historical)}],
        })
    elif defect == 'entry-limit':
        limits['max_entries'] = 1
        (historical / 'one').touch()
        (historical / 'two').touch()
    elif defect == 'byte-limit':
        limits['max_scanned_bytes'] = 1
        (historical / 'two-bytes.bin').write_bytes(b'xx')
    else:
        forbidden = tmp_path / 'held-out-secret'
        forbidden.mkdir()
        search = _write(tmp_path / 'inventory/held-out.json', {
            'schema': 'memory-family-namespace-search-v3',
            'roots': [{'kind': 'historical', 'path': str(forbidden)},
                      {'kind': 'training', 'path': str(training)}],
        })
    with patch.object(allocation, 'INVENTORY_LIMITS', limits):
        if defect == 'held-out':
            with patch.object(allocation.os, 'fwalk', side_effect=AssertionError('held-out root read')):
                with pytest.raises(ValueError):
                    allocation.build_namespace_inventory(search)
        else:
            with pytest.raises((OSError, ValueError)):
                allocation.build_namespace_inventory(search)


@pytest.mark.parametrize('collision', ['run', 'authored'])
def test_built_inventory_makes_producer_reject_historical_identity_reuse(tmp_path, collision):
    values = _contract_inputs(tmp_path)
    search, historical, _ = _search_manifest(tmp_path)
    if collision == 'run':
        reused = values['run_ids'][0]
    else:
        reused = values['slots']['cases'][0]['case_id']
    _write(historical / 'collision.json', {'id': reused})
    inventory = allocation.build_namespace_inventory(search)
    _write(values['inventory_path'], inventory['namespace'])
    with pytest.raises(ValueError, match='collides with retained history'):
        _build(values)


def test_admission_rejects_training_seed_reuse_and_search_drift(tmp_path):
    family_seed = 2**29
    inputs = _admission_inputs(tmp_path / 'seed', training_seed=family_seed)
    with pytest.raises(ValueError, match='training seed'):
        _admit(inputs)
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()

    inputs = _admission_inputs(tmp_path / 'drift')
    _write(inputs['historical'] / 'late.json', {'id': 'late-history'})
    with pytest.raises(ValueError, match='namespace inventory'):
        _admit(inputs)
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_capacity_uses_existing_root_bytes_and_one_shared_filesystem(tmp_path):
    inputs = _admission_inputs(tmp_path)
    roots = inputs['registration']['roots']
    used = Path(inputs['registration_path']).stat().st_size
    required = allocation.ALLOCATION_MAX_BYTES - used + allocation.MIN_FREE_BYTES
    disk = SimpleNamespace(free=required, total=required + 1, used=1)
    with patch('palimpsest.storage.shutil.disk_usage', return_value=disk):
        result = allocation._capacity(roots)
    assert result['used_bytes'] == used
    assert result['additional_bytes'] == allocation.ALLOCATION_MAX_BYTES - used
    assert result['required_free_bytes'] == required
    assert result['shortfall_bytes'] == 0
    assert result['max_entries'] == 131_072

    disk = SimpleNamespace(free=required - 1, total=required, used=1)
    with patch('palimpsest.storage.shutil.disk_usage', return_value=disk), \
            pytest.raises(Exception, match='free-space'):
        allocation._capacity(roots)


def test_current_style_missing_upstream_and_capacity_refuse_together_without_publication(tmp_path):
    inputs = _admission_inputs(tmp_path)
    capacity_error = allocation.StorageLimitError(
        'Storage free-space floor reached: free=1, additional=2, headroom=0, floor=3')
    with patch.object(allocation, '_capacity', side_effect=capacity_error), \
            patch.object(allocation, '_upstream_identity',
                         side_effect=ValueError('upstream/fly-gym is not initialized')):
        with pytest.raises(allocation.AdmissionRefused) as caught:
            allocation.admit(inputs['registration_path'], inputs['search'], ROOT,
                             ROOT / 'fixture-assets')
    assert str(caught.value) == (
        'Allocation refused: storage: Storage free-space floor reached: free=1, '
        'additional=2, headroom=0, floor=3; upstream: upstream/fly-gym is not initialized')
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_profile_and_runtime_identity_are_bound_without_importing_models():
    forbidden = {'torch', 'mujoco', 'flygym'}
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split('.')[0] in forbidden:
            raise AssertionError(f'model/runtime import attempted: {name}')
        return original(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=guarded):
        runtime = allocation._runtime_identity(ROOT)
        profile = allocation._profile_identity()
    assert runtime['python']['major_minor'] == [3, 11]
    assert set(runtime['distributions']) == set(allocation.PROTOCOL['runtime']['distributions'])
    assert set(runtime['project_files']) == {'pyproject.toml', 'uv.lock'}
    assert profile == allocation.PROTOCOL['profile']


def test_missing_or_different_upstream_tree_rejects_without_git_process(tmp_path):
    repo = tmp_path / 'repo'
    (repo / 'upstream/fly-gym').mkdir(parents=True)
    with patch('subprocess.Popen', side_effect=AssertionError('subprocess')), \
            patch('subprocess.run', side_effect=AssertionError('subprocess')), \
            patch('subprocess.check_output', side_effect=AssertionError('subprocess')):
        with pytest.raises(ValueError, match='initialized'):
            allocation._upstream_identity(repo)
        git_dir = repo / '.git/modules/upstream/fly-gym'
        git_dir.mkdir(parents=True)
        (git_dir / 'HEAD').write_text(UPSTREAM_IDENTITY['commit'] + '\n')
        (repo / 'upstream/fly-gym/.git').write_text(
            'gitdir: ../../.git/modules/upstream/fly-gym\n')
        (repo / 'upstream/fly-gym/untracked.txt').write_text('different')
        with pytest.raises(ValueError, match='tree'):
            allocation._upstream_identity(repo)


def test_success_is_exclusive_zero_owner_and_canonical(tmp_path):
    inputs = _admission_inputs(tmp_path)
    forbidden = AssertionError('allocation attempted execution')
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split('.')[0] in {'torch', 'mujoco', 'flygym'}:
            raise forbidden
        return original(name, *args, **kwargs)

    with patch('palimpsest.engine.Engine.open', side_effect=forbidden), \
            patch('subprocess.Popen', side_effect=forbidden), \
            patch('subprocess.run', side_effect=forbidden), \
            patch('subprocess.check_output', side_effect=forbidden), \
            patch('builtins.__import__', side_effect=guarded):
        descriptor = _admit(inputs)

    target = Path(descriptor['path'])
    admission = artifacts._json(target.read_bytes())
    assert target == inputs['values']['roots']['publication'] / 'allocation-admission.json'
    assert target.read_bytes() == memory.canonical_bytes(admission)
    assert descriptor['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert admission['storage_allocation_admitted'] is True
    assert admission['native_owner_launch_authorized'] is False
    assert admission['native_allocation'] is False
    assert admission['held_out_used'] is False
    assert admission['qualification_claims'] == []
    assert admission['registration']['sha256'] == hashlib.sha256(
        Path(inputs['registration_path']).read_bytes()).hexdigest()
    assert admission['identity']['upstream'] == UPSTREAM_IDENTITY
    assert admission['identity']['assets_model'] == ASSET_MODEL_IDENTITY
    assert admission['namespace']['searched_roots_sha256'] == (
        inputs['inventory']['search']['searched_roots_sha256'])
    assert not inputs['values']['roots']['output'].exists()
    assert not inputs['values']['roots']['control'].exists()
    with pytest.raises(FileExistsError):
        _admit(inputs)


@pytest.mark.parametrize('failure', ['link', 'directory-fsync', 'second-scan'])
def test_publication_failure_or_second_scan_drift_rolls_back(tmp_path, failure):
    inputs = _admission_inputs(tmp_path)
    target = inputs['values']['roots']['publication'] / 'allocation-admission.json'
    if failure == 'link':
        context = patch.object(allocation.os, 'link', side_effect=OSError('link failed'))
    elif failure == 'directory-fsync':
        actual = allocation.os.fsync
        calls = 0

        def fail_second(descriptor):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('directory fsync failed')
            return actual(descriptor)
        context = patch.object(allocation.os, 'fsync', side_effect=fail_second)
    else:
        def mutate(*_):
            _write(inputs['historical'] / 'late.json', {'id': 'late'})
            return ASSET_MODEL_IDENTITY
        context = patch.object(allocation, '_asset_model_identity', side_effect=mutate)
    with context, patch.object(allocation, '_capacity', return_value=_capacity()), \
            patch.object(allocation, '_upstream_identity', return_value=UPSTREAM_IDENTITY):
        if failure == 'second-scan':
            call = lambda: allocation.admit(
                inputs['registration_path'], inputs['search'], ROOT,
                ROOT / 'fixture-assets')
        else:
            call = lambda: _admit(inputs)
        with pytest.raises((OSError, RuntimeError), match='failed|changed'):
            call()
    assert not target.exists()
    assert not list(target.parent.glob(f'.{target.name}.*.tmp'))

