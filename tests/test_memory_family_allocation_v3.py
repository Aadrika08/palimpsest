"""Synthetic zero-owner allocation checks; no model, subprocess, or study runs."""
import ast
import copy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
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
SOURCE_IDS = ('pre-heldout-development-history', 'training-namespace')
UPSTREAM_IDENTITY = {
    'path': '/fixture/repo/upstream/fly-gym',
    'commit': '8d964599119b420de67ee259434d273651a1a76d',
    'files': 122,
    'bytes': 21_280_722,
    'inventory_sha256': 'ad06f7682f3c403f5b3b53d06e57594ffcb868997204796c6fba40b281b096bc',
}
ASSET_MODEL_IDENTITY = {
    'manifest': {'path': '/fixture/repo/model_manifests/flynn-full-vision.json',
                 'bytes': 1, 'sha256':
                 'e319bb18e12110dbc096d62d3d6e9550c7b37434bf5e18e410c5410c21bb97e5'},
    'assets': {'fixture': True}, 'model': {'fixture': True},
    'prepared_graph': {'fixture': True},
}


def _export(root, source_id, kind, *, known_sources, run_ids=(), authored=(), seeds=()):
    root.mkdir(parents=True, exist_ok=True)
    return _write(root / 'namespace-export.json', {
        'schema': 'memory-family-namespace-export-v3',
        'source_id': source_id,
        'kind': kind,
        'known_sources': sorted(known_sources),
        'historical_run_ids': sorted(run_ids),
        'historical_authored_ids': sorted(authored),
        'training_seeds': sorted(seeds),
    })


def _expected(root):
    path = root / 'namespace-export.json'
    payload = path.read_bytes()
    value = artifacts._json(payload)
    ledger = [{
        'path': path.name, 'kind': 'file', 'executable': False,
        'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
    }]
    return {
        'entries': 1, 'files': 1, 'bytes': len(payload),
        'inventory_sha256': memory.sha256(ledger),
        'export_bytes': len(payload),
        'export_sha256': hashlib.sha256(payload).hexdigest(),
        'known_sources_count': len(value['known_sources']),
        'known_sources_sha256': memory.sha256(value['known_sources']),
        'historical_run_ids_count': len(value['historical_run_ids']),
        'historical_run_ids_sha256': memory.sha256(value['historical_run_ids']),
        'historical_authored_ids_count': len(value['historical_authored_ids']),
        'historical_authored_ids_sha256': memory.sha256(
            value['historical_authored_ids']),
        'training_seeds_count': len(value['training_seeds']),
        'training_seeds_sha256': memory.sha256(value['training_seeds']),
    }


def _resolved_contract(historical, training):
    contract = copy.deepcopy(allocation.PROTOCOL['inventory'])
    contract.update(coverage_status='resolved', allocation_authorized=True,
                    reason=None)
    contract['sources'] = [
        {'source_id': SOURCE_IDS[0], 'kind': 'historical',
         'expected': _expected(historical)},
        {'source_id': SOURCE_IDS[1], 'kind': 'training',
         'expected': _expected(training)},
    ]
    return contract


def _paths(tmp_path, historical, training, sources=None):
    sources = sources or [
        {'source_id': SOURCE_IDS[0], 'path': str(historical)},
        {'source_id': SOURCE_IDS[1], 'path': str(training)},
    ]
    return _write(tmp_path / 'inventory/coverage-paths.json', {
        'schema': 'memory-family-namespace-paths-v3', 'sources': sources,
    })


def _coverage_fixture(tmp_path, *, training_seed=10):
    historical = tmp_path / 'namespace-exports/history'
    training = tmp_path / 'namespace-exports/training'
    _export(historical, SOURCE_IDS[0], 'historical',
            known_sources=['fixture-development-campaign'],
            authored=['retained-old-case'])
    _export(training, SOURCE_IDS[1], 'training',
            known_sources=['fixture-training-campaign'],
            authored=['trained-old-controller'], seeds=[training_seed])
    return (_paths(tmp_path, historical, training), historical, training,
            _resolved_contract(historical, training))


def _admission_inputs(tmp_path, *, training_seed=10):
    paths, historical, training, contract = _coverage_fixture(
        tmp_path, training_seed=training_seed)
    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        inventory = allocation.build_namespace_inventory(paths)
    values = _contract_inputs(tmp_path)
    _write(values['inventory_path'], inventory['namespace'])
    registration = _build(values)
    registration_path = _registration_file(values, registration)
    return {
        'paths': paths, 'historical': historical, 'training': training,
        'coverage': contract, 'inventory': inventory, 'values': values,
        'registration': registration, 'registration_path': registration_path,
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
    with ExitStack() as stack:
        stack.enter_context(patch.object(
            allocation, 'NAMESPACE_COVERAGE', inputs['coverage']))
        for name, value in defaults.items():
            stack.enter_context(patch.object(allocation, name, return_value=value))
        return allocation.admit(
            inputs['registration_path'], inputs['paths'], ROOT,
            ROOT / 'fixture-assets')


def test_protocol_freezes_capacity_and_an_unresolved_namespace_gate():
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
    assert protocol['inventory']['source_ids'] == list(SOURCE_IDS)
    assert protocol['inventory']['coverage_status'] == 'unresolved'
    assert protocol['inventory']['allocation_authorized'] is False
    assert all(row['expected'] is None for row in protocol['inventory']['sources'])
    assert protocol['result']['storage_allocation_admitted'] is False
    assert protocol['result']['allocation_authorized'] is False
    assert {row['id'] for row in protocol['behavior_sources']} == {
        'admission', 'producer', 'family_generator', 'artifacts', 'assets',
        'memory_core', 'family_world', 'storage', 'allocation_protocol',
    }


@pytest.mark.parametrize('mode', ['direct', 'module'])
def test_import_bootstrap_binds_checkout_without_running_preflight(mode):
    program = textwrap.dedent(r'''
        import dataclasses
        import json
        import os
        from pathlib import Path
        import runpy
        import sys

        mode, root_text = sys.argv[1:]
        root = Path(root_text).resolve()
        source = root / 'scripts/memory_family_allocation_v3.py'
        forbidden_calls = {'main', 'admit', 'build_namespace_inventory'}

        def trace(frame, event, _):
            if (event == 'call' and Path(frame.f_code.co_filename).resolve() == source
                    and frame.f_code.co_name in forbidden_calls):
                raise AssertionError(f'called {frame.f_code.co_name} during import')
            return trace

        def external_scan(*_, **__):
            raise AssertionError('external namespace scan during import')

        os.scandir = external_scan
        sys.settrace(trace)
        try:
            if mode == 'direct':
                namespace = runpy.run_path(str(source), run_name='allocation_import_only')
            else:
                sys.path.insert(0, str(root))
                namespace = runpy.run_module(
                    'scripts.memory_family_allocation_v3',
                    run_name='allocation_import_only')
        finally:
            sys.settrace(None)

        storage = sys.modules['palimpsest.storage']
        origins = {
            'artifacts': str(Path(namespace['artifacts'].__file__).resolve()),
            'producer': str(Path(namespace['producer'].__file__).resolve()),
            'storage': str(Path(storage.__file__).resolve()),
        }
        assert origins == {
            'artifacts': str(root / 'src/palimpsest/artifacts.py'),
            'producer': str(root / 'scripts/memory_family_producer_v3.py'),
            'storage': str(root / 'src/palimpsest/storage.py'),
        }
        field = next(item for item in dataclasses.fields(namespace['StorageLimits'])
                     if item.name == 'max_entries')
        assert field.default == 100_000
        assert namespace['StorageLimits'](
            max_bytes=1, min_free_bytes=0, max_entries=131_072).max_entries == 131_072
        print(json.dumps({'mode': mode, 'origins': origins}, sort_keys=True))
    ''')
    completed = subprocess.run(
        [sys.executable, '-I', '-c', program, mode, str(ROOT)],
        cwd='/tmp', text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr


def test_unresolved_coverage_refuses_before_any_external_root_read(tmp_path):
    paths = _write(tmp_path / 'coverage-paths.json', {
        'schema': 'memory-family-namespace-paths-v3',
        'sources': [
            {'source_id': SOURCE_IDS[0], 'path': '/not/read/history'},
            {'source_id': SOURCE_IDS[1], 'path': '/not/read/training'},
        ],
    })
    with patch.object(allocation.os, 'scandir',
                      side_effect=AssertionError('external root read')):
        with pytest.raises(allocation.AdmissionRefused, match='unresolved'):
            allocation.build_namespace_inventory(paths)


def test_unresolved_production_gate_cannot_publish_or_reach_assets(tmp_path):
    inputs = _admission_inputs(tmp_path)
    forbidden = AssertionError('external namespace or asset read')
    with patch.object(allocation.os, 'scandir', side_effect=forbidden), \
            patch.object(allocation, '_capacity', return_value=_capacity()), \
            patch.object(allocation, '_upstream_identity',
                         return_value=UPSTREAM_IDENTITY), \
            patch.object(allocation, '_asset_model_identity',
                         side_effect=forbidden):
        with pytest.raises(allocation.AdmissionRefused,
                           match='namespace: Namespace coverage unresolved'):
            allocation.admit(inputs['registration_path'], inputs['paths'], ROOT,
                             ROOT / 'fixture-assets')
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_forbidden_partition_reference_refuses_before_producer_reads_it(tmp_path):
    inputs = _admission_inputs(tmp_path)
    registration = artifacts._json(inputs['registration_path'].read_bytes())
    relation = next(iter(registration['histories']))
    registration['histories'][relation]['path'] = '/tmp/held-out-do-not-read.json'
    _write(inputs['registration_path'], registration)
    with patch.object(allocation.producer, '_registration',
                      side_effect=AssertionError('producer opened held-out input')):
        with pytest.raises(ValueError, match='held-out'):
            allocation.admit(inputs['registration_path'], inputs['paths'], ROOT,
                             ROOT / 'fixture-assets')
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_exact_namespace_exports_build_complete_bounded_inventory(tmp_path):
    inline_run = uuid.UUID(int=71).hex
    second_run = uuid.UUID(int=72).hex
    historical = tmp_path / 'namespace-exports/history'
    training = tmp_path / 'namespace-exports/training'
    _export(historical, SOURCE_IDS[0], 'historical',
            known_sources=['development-a', 'development-b'],
            run_ids=[inline_run, second_run], authored=['old-case', 'old-subject'])
    _export(training, SOURCE_IDS[1], 'training',
            known_sources=['training-a'], authored=['trained-agent'], seeds=[10, 11, 12])
    paths = _paths(tmp_path, historical, training)
    contract = _resolved_contract(historical, training)

    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        result = allocation.build_namespace_inventory(paths)

    assert result['namespace'] == {
        'schema': 'memory-family-namespace-inventory-v3',
        'historical_run_ids': [inline_run, second_run],
        'historical_authored_ids': ['old-case', 'old-subject', 'trained-agent'],
    }
    assert result['coverage']['training_seeds'] == [10, 11, 12]
    assert result['coverage']['training_seeds_sha256'] == memory.sha256([10, 11, 12])
    assert result['coverage']['known_sources'] == [
        'development-a', 'development-b', 'training-a']
    roots = result['coverage']['roots']
    assert [(row['source_id'], row['kind'], row['entries'], row['files'])
            for row in roots] == [
        (SOURCE_IDS[0], 'historical', 1, 1),
        (SOURCE_IDS[1], 'training', 1, 1),
    ]
    assert result['coverage']['searched_roots_sha256'] == memory.sha256(roots)
    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        assert result == allocation.build_namespace_inventory(paths)


def test_frozen_export_identity_is_portable_across_manifest_roots(tmp_path):
    _, historical, training, contract = _coverage_fixture(tmp_path / 'frozen')
    relocated_history = tmp_path / 'relocated/history'
    relocated_training = tmp_path / 'relocated/training'
    _export(relocated_history, SOURCE_IDS[0], 'historical',
            known_sources=['fixture-development-campaign'],
            authored=['retained-old-case'])
    _export(relocated_training, SOURCE_IDS[1], 'training',
            known_sources=['fixture-training-campaign'],
            authored=['trained-old-controller'], seeds=[10])
    paths = _paths(tmp_path / 'relocated', relocated_history, relocated_training)

    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        result = allocation.build_namespace_inventory(paths)

    assert [row['path'] for row in result['coverage']['roots']] == [
        str(relocated_history), str(relocated_training)]


def test_export_root_enumeration_stops_after_second_entry(tmp_path):
    paths, historical, _, contract = _coverage_fixture(tmp_path)

    class TooManyEntries:
        def __init__(self):
            self.count = 0

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            return self

        def __next__(self):
            self.count += 1
            if self.count > 2:
                raise AssertionError('enumerated beyond the rejection bound')
            return SimpleNamespace(name=f'entry-{self.count}')

    entries = TooManyEntries()
    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract), \
            patch.object(allocation.os, 'scandir', return_value=entries):
        with pytest.raises(ValueError, match='one-file allowlist'):
            allocation.build_namespace_inventory(paths)
    assert entries.count == 2


@pytest.mark.parametrize('defect', [
    'missing-source', 'unknown-source', 'extra-file', 'subdirectory',
    'malformed', 'noncanonical', 'oversized', 'symlink', 'special',
    'overlap', 'identity-drift', 'held-out',
])
def test_namespace_coverage_rejects_unfrozen_or_unsafe_inputs(tmp_path, defect):
    paths, historical, training, contract = _coverage_fixture(tmp_path)
    export = historical / 'namespace-export.json'
    if defect == 'missing-source':
        paths = _paths(tmp_path, historical, training, [
            {'source_id': SOURCE_IDS[0], 'path': str(historical)}])
    elif defect == 'unknown-source':
        paths = _paths(tmp_path, historical, training, [
            {'source_id': SOURCE_IDS[0], 'path': str(historical)},
            {'source_id': 'caller-selected-root', 'path': str(training)}])
    elif defect == 'extra-file':
        (historical / 'evidence.json').write_text('{}')
    elif defect == 'subdirectory':
        (historical / 'runs').mkdir()
    elif defect == 'malformed':
        export.write_text('{')
    elif defect == 'noncanonical':
        value = artifacts._json(export.read_bytes())
        export.write_text(json.dumps(value, indent=2) + '\n')
    elif defect == 'oversized':
        contract['max_metadata_bytes'] = export.stat().st_size - 1
    elif defect == 'symlink':
        target = tmp_path / 'outside.json'
        target.write_bytes(export.read_bytes())
        export.unlink()
        export.symlink_to(target)
    elif defect == 'special':
        export.unlink()
        os.mkfifo(export)
    elif defect == 'overlap':
        paths = _paths(tmp_path, historical, training, [
            {'source_id': SOURCE_IDS[0], 'path': str(historical)},
            {'source_id': SOURCE_IDS[1], 'path': str(historical)}])
    elif defect == 'identity-drift':
        value = artifacts._json(export.read_bytes())
        value['historical_authored_ids'].append('late')
        _write(export, value)
    else:
        forbidden = tmp_path / 'held-out-secret'
        forbidden.mkdir()
        paths = _paths(tmp_path, forbidden, training)
    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        if defect == 'held-out':
            with patch.object(allocation.os, 'scandir',
                              side_effect=AssertionError('held-out root read')):
                with pytest.raises(ValueError):
                    allocation.build_namespace_inventory(paths)
        else:
            with pytest.raises((OSError, ValueError)):
                allocation.build_namespace_inventory(paths)


@pytest.mark.parametrize('collision', ['run', 'authored'])
def test_built_inventory_makes_producer_reject_historical_identity_reuse(tmp_path, collision):
    values = _contract_inputs(tmp_path)
    paths, historical, training, _ = _coverage_fixture(tmp_path)
    export = artifacts._json((historical / 'namespace-export.json').read_bytes())
    if collision == 'run':
        export['historical_run_ids'] = [values['run_ids'][0]]
    else:
        export['historical_authored_ids'] = [values['slots']['cases'][0]['case_id']]
    _write(historical / 'namespace-export.json', export)
    contract = _resolved_contract(historical, training)
    with patch.object(allocation, 'NAMESPACE_COVERAGE', contract):
        inventory = allocation.build_namespace_inventory(paths)
    _write(values['inventory_path'], inventory['namespace'])
    with pytest.raises(ValueError, match='collides with retained history'):
        _build(values)


def test_admission_rejects_training_seed_reuse_and_export_drift(tmp_path):
    inputs = _admission_inputs(tmp_path / 'seed', training_seed=2**29)
    with pytest.raises(ValueError, match='training seed'):
        _admit(inputs)
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()

    inputs = _admission_inputs(tmp_path / 'drift')
    export = inputs['historical'] / 'namespace-export.json'
    changed = artifacts._json(export.read_bytes())
    changed['historical_authored_ids'].append('late-history')
    changed['historical_authored_ids'].sort()
    _write(export, changed)
    with pytest.raises(allocation.AdmissionRefused,
                       match='namespace: .*namespace export|namespace: .*coverage'):
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


def test_capacity_and_missing_upstream_refuse_together_without_publication(tmp_path):
    inputs = _admission_inputs(tmp_path)
    capacity_error = allocation.StorageLimitError(
        'Storage free-space floor reached: free=1, additional=2, headroom=0, floor=3')
    with patch.object(allocation, 'NAMESPACE_COVERAGE', inputs['coverage']), \
            patch.object(allocation, '_capacity', side_effect=capacity_error), \
            patch.object(allocation, '_upstream_identity',
                         side_effect=ValueError('upstream/fly-gym is not initialized')):
        with pytest.raises(allocation.AdmissionRefused) as caught:
            allocation.admit(inputs['registration_path'], inputs['paths'], ROOT,
                             ROOT / 'fixture-assets')
    assert str(caught.value) == (
        'Allocation refused: storage: Storage free-space floor reached: free=1, '
        'additional=2, headroom=0, floor=3; upstream: upstream/fly-gym is not initialized')
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_identity_checks_never_load_construct_or_run_a_model():
    forbidden = AssertionError('model construction/load/inference attempted')
    with patch('palimpsest.engine.Engine.open', side_effect=forbidden), \
            patch('palimpsest.assets.prepare_graph', side_effect=forbidden), \
            patch('palimpsest.flynn.load_policy', side_effect=forbidden), \
            patch('palimpsest.male_policy.load_pinned_policy', side_effect=forbidden), \
            patch('subprocess.Popen', side_effect=forbidden), \
            patch('subprocess.run', side_effect=forbidden), \
            patch('subprocess.check_output', side_effect=forbidden):
        runtime = allocation._runtime_identity(ROOT)
        profile = allocation._profile_identity()
        behavior = allocation._behavior_identity(ROOT)
    assert runtime['python']['major_minor'] == [3, 11]
    assert set(runtime['distributions']) == set(allocation.PROTOCOL['runtime']['distributions'])
    assert set(runtime['project_files']) == {'pyproject.toml', 'uv.lock'}
    assert profile == allocation.PROTOCOL['profile']
    assert set(behavior) == {row['id'] for row in allocation.PROTOCOL['behavior_sources']}
    assert all(set(row) == {'path', 'bytes', 'sha256'} for row in behavior.values())


def test_admission_refuses_source_bytes_different_from_loaded_code(tmp_path):
    inputs = _admission_inputs(tmp_path)
    drifted = allocation._behavior_identity(ROOT)
    drifted['storage']['sha256'] = '0' * 64
    with patch.object(allocation, '_behavior_identity', return_value=drifted):
        with pytest.raises(RuntimeError, match='loaded|executing'):
            _admit(inputs)
    assert not (inputs['values']['roots']['publication'] /
                'allocation-admission.json').exists()


def test_admission_source_has_no_model_runtime_or_subprocess_call_path():
    tree = ast.parse(Path(allocation.__file__).read_text())
    imports, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
        elif isinstance(node, ast.Call):
            calls.add(ast.unparse(node.func))
    assert not imports.intersection({'torch', 'mujoco', 'flygym', 'subprocess'})
    assert not calls.intersection({
        'Engine.open', 'prepare_graph', 'load_policy', 'load_pinned_policy',
        'subprocess.run', 'subprocess.Popen', 'subprocess.check_output',
    })


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


def test_upstream_gitdir_must_stay_in_repository_metadata(tmp_path):
    repo = tmp_path / 'repo'
    upstream = repo / 'upstream/fly-gym'
    upstream.mkdir(parents=True)
    external = tmp_path / 'external-git'
    external.mkdir()
    (external / 'HEAD').write_text('1' * 40 + '\n')
    (upstream / '.git').write_text(f'gitdir: {external}\n')
    protocol = copy.deepcopy(allocation.PROTOCOL)
    protocol['upstream'] = {
        'path': 'upstream/fly-gym', 'commit': '1' * 40,
        'files': 0, 'bytes': 0, 'inventory_sha256': memory.sha256([]),
    }
    with patch.object(allocation, 'PROTOCOL', protocol):
        with pytest.raises(ValueError, match='repository.*metadata'):
            allocation._upstream_identity(repo)


def test_upstream_gitdir_accepts_exact_linked_worktree_metadata(tmp_path):
    repo = tmp_path / 'repo'
    upstream = repo / 'upstream/fly-gym'
    upstream.mkdir(parents=True)
    checkout_git = tmp_path / 'main.git/worktrees/allocation'
    git_dir = checkout_git / 'modules/upstream/fly-gym'
    git_dir.mkdir(parents=True)
    (repo / '.git').write_text(f'gitdir: {checkout_git}\n')
    relative = os.path.relpath(git_dir, upstream)
    (upstream / '.git').write_text(f'gitdir: {relative}\n')
    (git_dir / 'HEAD').write_text('1' * 40 + '\n')
    protocol = copy.deepcopy(allocation.PROTOCOL)
    protocol['upstream'] = {
        'path': 'upstream/fly-gym', 'commit': '1' * 40,
        'files': 0, 'bytes': 0, 'inventory_sha256': memory.sha256([]),
    }
    with patch.object(allocation, 'PROTOCOL', protocol):
        result = allocation._upstream_identity(repo)
    assert result['commit'] == '1' * 40
    assert result['files'] == result['bytes'] == 0


def test_upstream_rejects_forbidden_gitdir_before_reading_head(tmp_path):
    repo = tmp_path / 'repo'
    upstream = repo / 'upstream/fly-gym'
    upstream.mkdir(parents=True)
    forbidden = tmp_path / 'held-out-private-git'
    forbidden.mkdir()
    (forbidden / 'HEAD').write_text('1' * 40 + '\n')
    (upstream / '.git').write_text(f'gitdir: {forbidden}\n')
    actual_read = allocation.artifacts._read

    def guarded_read(path, limit):
        if Path(path) == forbidden / 'HEAD':
            raise AssertionError('forbidden HEAD was read')
        return actual_read(path, limit)

    with patch.object(allocation.artifacts, '_read', side_effect=guarded_read):
        with pytest.raises(ValueError, match='held-out'):
            allocation._upstream_identity(repo)


def test_clean_upstream_tree_identity_uses_full_content_without_git(tmp_path):
    repo = tmp_path / 'repo'
    upstream = repo / 'upstream/fly-gym'
    git_dir = repo / '.git/modules/upstream/fly-gym'
    (upstream / 'nested').mkdir(parents=True)
    git_dir.mkdir(parents=True)
    (git_dir / 'HEAD').write_text('1' * 40 + '\n')
    (upstream / '.git').write_text(
        'gitdir: ../../.git/modules/upstream/fly-gym\n')
    (upstream / 'root.txt').write_bytes(b'root')
    (upstream / 'nested/child.txt').write_bytes(b'child')
    rows = [
        {'path': 'root.txt', 'kind': 'file', 'executable': False,
         'bytes': 4, 'sha256': hashlib.sha256(b'root').hexdigest()},
        {'path': 'nested/child.txt', 'kind': 'file', 'executable': False,
         'bytes': 5, 'sha256': hashlib.sha256(b'child').hexdigest()},
    ]
    protocol = copy.deepcopy(allocation.PROTOCOL)
    protocol['upstream'] = {
        'path': 'upstream/fly-gym', 'commit': '1' * 40,
        'files': 2, 'bytes': 9, 'inventory_sha256': memory.sha256(rows),
    }
    with patch.object(allocation, 'PROTOCOL', protocol), \
            patch('subprocess.Popen', side_effect=AssertionError('subprocess')), \
            patch('subprocess.run', side_effect=AssertionError('subprocess')), \
            patch('subprocess.check_output', side_effect=AssertionError('subprocess')):
        result = allocation._upstream_identity(repo)
    assert result == {
        'path': str(upstream), 'commit': '1' * 40, 'files': 2, 'bytes': 9,
        'inventory_sha256': memory.sha256(rows),
    }


@pytest.mark.parametrize('escape', ['edge', 'mapping'])
def test_prepared_graph_paths_must_stay_below_graph_root(tmp_path, escape):
    repo, root = tmp_path / 'repo', tmp_path / 'assets'
    manifest_path = repo / 'model_manifests/flynn-full-vision.json'
    manifest_path.parent.mkdir(parents=True)
    manifest_payload = b'fixture-manifest'
    manifest_path.write_bytes(manifest_payload)
    root.mkdir()
    (root / 'archive.7z').write_bytes(b'archive')
    (root / 'checkpoint.pt').write_bytes(b'checkpoint')
    archive_sha = 'a' * 64
    graph_root = root / f'graph-{archive_sha}'
    (graph_root / 'nested').mkdir(parents=True)
    outside = tmp_path / 'outside-graph'
    outside.mkdir()
    edge = outside / 'edge.bin' if escape == 'edge' else graph_root / 'nested/edge.bin'
    edge.write_bytes(b'edge')
    mapping = outside / 'mapping.json'
    mapping.write_bytes(b'mapping')
    edge_path = str(edge) if escape == 'edge' else 'nested/edge.bin'
    mapping_path = str(mapping) if escape == 'mapping' else 'mapping.json'
    if escape == 'edge':
        (outside / 'mapping.json').write_bytes(b'mapping')
    _write(graph_root / 'palimpsest-prepared.json', {
        'archive_sha256': archive_sha, 'upstream_commit': 'fixture-upstream',
        'edge_path': edge_path,
    })
    manifest = {
        'profile_id': 'flynn-full-vision', 'upstream_commit': 'fixture-upstream',
        'files': [
            {'id': 'graph_archive', 'path': 'archive.7z', 'sha256': archive_sha},
            {'id': 'checkpoint', 'path': 'checkpoint.pt'},
        ],
        'graph': {
            'edge_identity': {'size_bytes': 4,
                              'sha256': hashlib.sha256(b'edge').hexdigest()},
            'mapping_files': [{
                'path': mapping_path, 'size_bytes': 7,
                'sha256': hashlib.sha256(b'mapping').hexdigest(),
            }],
        },
    }
    protocol = copy.deepcopy(allocation.PROTOCOL)
    protocol['assets']['manifest_sha256'] = hashlib.sha256(manifest_payload).hexdigest()
    with patch.object(allocation, 'PROTOCOL', protocol), \
            patch.object(allocation.model_assets, 'load_manifest', return_value=manifest), \
            patch.object(allocation.model_assets, 'verify_assets', return_value={'ok': True}), \
            patch.object(allocation.model_assets, '_check_mappings', return_value=None):
        with pytest.raises(ValueError, match='graph root'):
            allocation._asset_model_identity(repo, root)


def test_registration_is_validated_from_prechecked_bytes_without_reopen(tmp_path):
    inputs = _admission_inputs(tmp_path)
    with patch.object(allocation.producer, '_registration',
                      side_effect=AssertionError('registration pathname reopened')):
        descriptor = _admit(inputs)
    assert Path(descriptor['path']).is_file()


def test_resolved_fixture_success_is_exclusive_zero_owner_and_canonical(tmp_path):
    inputs = _admission_inputs(tmp_path)
    forbidden = AssertionError('allocation attempted execution')
    with patch('palimpsest.engine.Engine.open', side_effect=forbidden), \
            patch('palimpsest.assets.prepare_graph', side_effect=forbidden), \
            patch('palimpsest.flynn.load_policy', side_effect=forbidden), \
            patch('palimpsest.male_policy.load_pinned_policy', side_effect=forbidden), \
            patch('subprocess.Popen', side_effect=forbidden), \
            patch('subprocess.run', side_effect=forbidden), \
            patch('subprocess.check_output', side_effect=forbidden):
        descriptor = _admit(inputs)

    target = Path(descriptor['path'])
    admission = artifacts._json(target.read_bytes())
    assert target == inputs['values']['roots']['publication'] / 'allocation-admission.json'
    assert target.read_bytes() == memory.canonical_bytes(admission)
    assert descriptor['bytes'] == target.stat().st_size
    assert descriptor['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert admission['storage_allocation_admitted'] is True
    assert admission['allocation_authorized'] is True
    assert admission['namespace_coverage_complete'] is True
    assert admission['native_owner_launch_authorized'] is False
    assert admission['native_allocation'] is False
    assert admission['held_out_used'] is False
    assert admission['qualification_claims'] == []
    assert admission['registration']['sha256'] == hashlib.sha256(
        Path(inputs['registration_path']).read_bytes()).hexdigest()
    assert admission['identity']['upstream'] == UPSTREAM_IDENTITY
    assert admission['identity']['assets_model'] == ASSET_MODEL_IDENTITY
    assert admission['namespace']['searched_roots_sha256'] == (
        inputs['inventory']['coverage']['searched_roots_sha256'])
    assert set(admission['identity']['behavior_sources']) == {
        row['id'] for row in allocation.PROTOCOL['behavior_sources']}
    assert not inputs['values']['roots']['output'].exists()
    assert not inputs['values']['roots']['control'].exists()
    with pytest.raises(FileExistsError):
        _admit(inputs)


@pytest.mark.parametrize('failure', ['link', 'commit-fsync', 'post-link-drift'])
def test_publication_failure_after_or_before_link_rolls_back_durably(tmp_path, failure):
    inputs = _admission_inputs(tmp_path)
    target = inputs['values']['roots']['publication'] / 'allocation-admission.json'
    if failure == 'link':
        context = patch.object(allocation.os, 'link', side_effect=OSError('link failed'))
    elif failure == 'commit-fsync':
        actual = allocation.os.fsync
        calls = 0

        def fail_commit(descriptor):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('commit fsync failed')
            return actual(descriptor)
        context = patch.object(allocation.os, 'fsync', side_effect=fail_commit)
    else:
        first = allocation._behavior_identity(ROOT)
        second = copy.deepcopy(first)
        second['storage']['sha256'] = '0' * 64
        context = patch.object(allocation, '_behavior_identity',
                               side_effect=[first, second])
    with context:
        with pytest.raises((OSError, RuntimeError), match='failed|changed'):
            _admit(inputs)
    assert not target.exists()
    assert not list(target.parent.glob(f'.{target.name}.*.tmp'))


def test_unprovable_post_link_rollback_surfaces_indeterminate_state(tmp_path):
    inputs = _admission_inputs(tmp_path)
    first = allocation._behavior_identity(ROOT)
    second = copy.deepcopy(first)
    second['storage']['sha256'] = '0' * 64
    with patch.object(allocation, '_behavior_identity', side_effect=[first, second]), \
            patch.object(allocation, '_durable_rollback',
                         side_effect=OSError('rollback directory fsync failed')):
        with pytest.raises(allocation.PublicationIndeterminate,
                           match='rollback.*indeterminate'):
            _admit(inputs)


def test_rollback_never_unlinks_a_replacement_inode(tmp_path):
    inputs = _admission_inputs(tmp_path)
    target = inputs['values']['roots']['publication'] / 'allocation-admission.json'
    first = allocation._behavior_identity(ROOT)
    second = copy.deepcopy(first)
    second['storage']['sha256'] = '0' * 64
    calls = 0

    def replace_then_drift(_):
        nonlocal calls
        calls += 1
        if calls == 1:
            return first
        target.unlink()
        target.write_bytes(b'concurrent replacement')
        return second

    with patch.object(allocation, '_behavior_identity', side_effect=replace_then_drift):
        with pytest.raises(allocation.PublicationIndeterminate,
                           match='rollback.*indeterminate'):
            _admit(inputs)
    assert target.read_bytes() == b'concurrent replacement'
