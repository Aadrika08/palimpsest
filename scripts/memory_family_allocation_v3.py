"""Deterministic memory-family allocation preflight; never start an owner."""
from __future__ import annotations

import argparse
import copy
import hashlib
from importlib import metadata
import os
from pathlib import Path
import platform
import stat
import sys
import tempfile
import uuid

# Direct-file and module entry points must load this checkout, never an installed copy.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT / 'src'), str(REPO_ROOT)]

from palimpsest import (
    artifacts, assets as model_assets, memory,
    memory_decision_world as family_world,
)
from palimpsest.storage import StorageBudget, StorageLimitError, StorageLimits
from scripts import memory_family_producer_v3 as producer


MiB = 1024**2
PROTOCOL_PATH = REPO_ROOT / 'docs/plans/memory-family-allocation-admission-v3-protocol.json'
PROTOCOL_BYTES = PROTOCOL_PATH.read_bytes()
PROTOCOL = artifacts._json(PROTOCOL_BYTES)
if PROTOCOL_BYTES != memory.canonical_bytes(PROTOCOL):
    raise ValueError('Allocation-admission protocol must be canonical JSON')

NAMESPACE_COVERAGE = copy.deepcopy(PROTOCOL['inventory'])
ALLOCATION_MAX_BYTES = PROTOCOL['storage']['allocation_max_bytes']
MIN_FREE_BYTES = PROTOCOL['storage']['min_free_bytes']
MINIMUM_CAPACITY_BYTES = PROTOCOL['storage']['minimum_capacity_bytes']
MAX_RECEIPT = 4 * MiB


class AdmissionRefused(RuntimeError):
    """One or more deterministic preflight gates did not admit allocation."""


class PublicationIndeterminate(RuntimeError):
    """The final name was linked and durable rollback could not be proven."""


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _held_out(path: Path | str) -> bool:
    words = ('held-out', 'held_out', 'heldout')
    return any(any(word in part.lower() for word in words)
               for part in Path(path).parts)


def _safe_absolute(path, label, *, directory=None) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raise ValueError(f'{label} must be absolute')
    result = Path(os.path.abspath(raw))
    if _held_out(result):
        raise ValueError(f'{label} cannot name held-out data')
    if any(part.is_symlink() for part in (result, *result.parents)):
        raise ValueError(f'{label} cannot traverse symlinks')
    if directory is True and not result.is_dir():
        raise ValueError(f'{label} must be an existing directory')
    if directory is False and not result.is_file():
        raise ValueError(f'{label} must be an existing file')
    return result


def _hash_stream(stream) -> str:
    digest = hashlib.sha256()
    while block := stream.read(MiB):
        digest.update(block)
    return digest.hexdigest()


def _descriptor(path, *, label='Identity file') -> dict:
    path = _safe_absolute(path, label, directory=False)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f'{label} must be a regular file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            digest = _hash_stream(stream)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fingerprint = lambda value: (
        value.st_dev, value.st_ino, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns,
    )
    if fingerprint(before) != fingerprint(after):
        raise RuntimeError(f'{label} changed while hashing')
    return {'path': str(path), 'bytes': before.st_size, 'sha256': digest}


def _canonical_file(path, limit, label):
    path = _safe_absolute(path, label, directory=False)
    payload = artifacts._read(path, limit)
    value = artifacts._json(payload)
    if payload != memory.canonical_bytes(value):
        raise ValueError(f'{label} must be canonical JSON')
    return path, value, payload


def _coverage_paths(path):
    path, value, payload = _canonical_file(path, MiB, 'Namespace path manifest')
    if type(value) is not dict or set(value) != {'schema', 'sources'}:
        raise ValueError('Namespace path manifest has missing or unknown fields')
    if value['schema'] != 'memory-family-namespace-paths-v3':
        raise ValueError('Unknown namespace path manifest')
    sources = value['sources']
    expected_ids = NAMESPACE_COVERAGE['source_ids']
    if (type(sources) is not list or len(sources) != len(expected_ids)
            or any(type(row) is not dict or set(row) != {'source_id', 'path'}
                   for row in sources)
            or [row['source_id'] for row in sources] != expected_ids
            or any(type(row['path']) is not str for row in sources)):
        raise ValueError('Namespace path manifest must map the exact frozen sources')
    descriptor = {'path': str(path), 'bytes': len(payload),
                  'sha256': hashlib.sha256(payload).hexdigest()}
    return descriptor, sources


def _coverage_contract():
    contract = NAMESPACE_COVERAGE
    fields = {
        'schema', 'coverage_status', 'allocation_authorized', 'reason',
        'source_ids', 'export_schema', 'file_allowlist', 'sources',
        'max_identity_characters', 'max_metadata_bytes', 'max_values',
    }
    if type(contract) is not dict or set(contract) != fields:
        raise ValueError('Namespace coverage contract has missing or unknown fields')
    if (contract['schema'] != 'memory-family-namespace-coverage-v3'
            or contract['source_ids'] != [
                'pre-heldout-development-history', 'training-namespace']
            or contract['export_schema'] != 'memory-family-namespace-export-v3'
            or contract['file_allowlist'] != ['namespace-export.json']
            or type(contract['max_identity_characters']) is not int
            or not 1 <= contract['max_identity_characters'] <= 128
            or type(contract['max_metadata_bytes']) is not int
            or not 1 <= contract['max_metadata_bytes'] <= 32 * MiB
            or type(contract['max_values']) is not int
            or not 1 <= contract['max_values'] <= 100_000):
        raise ValueError('Unknown namespace coverage contract')
    sources = contract['sources']
    if (type(sources) is not list or len(sources) != 2
            or [row.get('source_id') for row in sources] != contract['source_ids']
            or [row.get('kind') for row in sources] != ['historical', 'training']
            or any(type(row) is not dict
                   or set(row) != {'source_id', 'kind', 'expected'}
                   for row in sources)):
        raise ValueError('Namespace coverage sources differ')
    if contract['coverage_status'] != 'resolved' or contract['allocation_authorized'] is not True:
        if (contract['coverage_status'] != 'unresolved'
                or contract['allocation_authorized'] is not False
                or not isinstance(contract['reason'], str)
                or any(row['expected'] is not None for row in sources)):
            raise ValueError('Invalid unresolved namespace coverage contract')
        raise AdmissionRefused('Namespace coverage unresolved: ' + contract['reason'])
    if contract['reason'] is not None or any(type(row['expected']) is not dict
                                             for row in sources):
        raise ValueError('Resolved namespace coverage requires exact identities')
    return contract


def _validated_list(value, label, validator):
    if type(value) is not list or value != sorted(value) or len(value) != len(set(value)):
        raise ValueError(f'{label} must be a sorted distinct list')
    for item in value:
        validator(item)
    return value


def _uuid(value):
    try:
        valid = type(value) is str and uuid.UUID(value).hex == value
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Historical run ID must be canonical UUID hex')


def _identifier(value):
    memory._id(value)
    try:
        forms = {uuid.UUID(value).hex, str(uuid.UUID(value))}
    except (AttributeError, ValueError):
        return
    if value in forms:
        raise ValueError('UUIDs belong in historical_run_ids')


def _read_export(path_row, source_contract, limits):
    source_id, kind = source_contract['source_id'], source_contract['kind']
    expected = source_contract['expected']
    expected_fields = {
        'entries', 'files', 'bytes', 'inventory_sha256',
        'export_bytes', 'export_sha256', 'known_sources_count',
        'known_sources_sha256', 'historical_run_ids_count',
        'historical_run_ids_sha256', 'historical_authored_ids_count',
        'historical_authored_ids_sha256', 'training_seeds_count',
        'training_seeds_sha256',
    }
    if set(expected) != expected_fields:
        raise ValueError(f'{source_id} frozen identity differs')
    root = Path(path_row['path'])
    if _held_out(root):
        raise ValueError('Namespace export cannot name held-out data')
    root = _safe_absolute(root, f'{source_id} root', directory=True)
    entries = []
    with os.scandir(root) as iterator:
        for entry in iterator:
            entries.append(entry)
            if len(entries) == 2:
                break
    if len(entries) != 1 or entries[0].name != 'namespace-export.json':
        raise ValueError(f'{source_id} root differs from the one-file allowlist')
    info = entries[0].stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or entries[0].is_symlink():
        raise ValueError(f'{source_id} export must be a direct regular file')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    directory_descriptor = os.open(
        root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        descriptor = os.open(entries[0].name, flags, dir_fd=directory_descriptor)
    finally:
        os.close(directory_descriptor)
    # Open a separate anchored directory descriptor explicitly so every path is
    # direct. The file descriptor remains valid if a caller races a pathname.
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limits['max_metadata_bytes']:
            raise ValueError(f'{source_id} export is missing or oversized')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            payload = stream.read(limits['max_metadata_bytes'] + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(payload) > limits['max_metadata_bytes']:
        raise ValueError(f'{source_id} export exceeds its read limit')
    fingerprint = lambda value: (
        value.st_dev, value.st_ino, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns,
    )
    if fingerprint(before) != fingerprint(after):
        raise RuntimeError(f'{source_id} namespace export changed while reading')
    export = artifacts._json(payload)
    if payload != memory.canonical_bytes(export):
        raise ValueError(f'{source_id} namespace export must be canonical JSON')
    fields = {
        'schema', 'source_id', 'kind', 'known_sources',
        'historical_run_ids', 'historical_authored_ids', 'training_seeds',
    }
    if (type(export) is not dict or set(export) != fields
            or export['schema'] != limits['export_schema']
            or export['source_id'] != source_id or export['kind'] != kind):
        raise ValueError(f'{source_id} namespace export schema differs')
    cap = limits['max_identity_characters']

    def known(value):
        if type(value) is not str or not value or len(value) > cap or _held_out(value):
            raise ValueError('Invalid or held-out known-source identity')

    _validated_list(export['known_sources'], 'Known sources', known)
    if not export['known_sources']:
        raise ValueError('Namespace export must enumerate at least one known source')
    _validated_list(export['historical_run_ids'], 'Historical run IDs', _uuid)
    _validated_list(export['historical_authored_ids'], 'Historical authored IDs',
                    _identifier)

    def seed(value):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError('Training seed must be a nonnegative 32-bit integer')

    _validated_list(export['training_seeds'], 'Training seeds', seed)
    if kind == 'historical' and export['training_seeds']:
        raise ValueError('Historical namespace export cannot declare training seeds')
    if sum(len(export[name]) for name in (
            'known_sources', 'historical_run_ids',
            'historical_authored_ids', 'training_seeds')) > limits['max_values']:
        raise ValueError('Namespace export exceeds its value limit')
    ledger = [{
        'path': 'namespace-export.json', 'kind': 'file',
        'executable': bool(before.st_mode & stat.S_IXUSR),
        'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
    }]
    actual = {
        'entries': 1, 'files': 1, 'bytes': len(payload),
        'inventory_sha256': memory.sha256(ledger),
        'export_bytes': len(payload),
        'export_sha256': hashlib.sha256(payload).hexdigest(),
        'known_sources_count': len(export['known_sources']),
        'known_sources_sha256': memory.sha256(export['known_sources']),
        'historical_run_ids_count': len(export['historical_run_ids']),
        'historical_run_ids_sha256': memory.sha256(export['historical_run_ids']),
        'historical_authored_ids_count': len(export['historical_authored_ids']),
        'historical_authored_ids_sha256': memory.sha256(
            export['historical_authored_ids']),
        'training_seeds_count': len(export['training_seeds']),
        'training_seeds_sha256': memory.sha256(export['training_seeds']),
    }
    if actual != expected:
        raise ValueError(f'{source_id} namespace export differs from frozen identity')
    receipt = {'source_id': source_id, 'kind': kind, 'path': str(root), **actual}
    return root, export, receipt


def build_namespace_inventory(search_manifest_path):
    """Read only the two protocol-frozen namespace exports; never evidence trees."""
    manifest, path_rows = _coverage_paths(search_manifest_path)
    contract = _coverage_contract()
    roots, exports, receipts = [], [], []
    for path_row, source_contract in zip(path_rows, contract['sources']):
        if path_row['source_id'] != source_contract['source_id']:
            raise ValueError('Namespace path source order differs')
        root, export, receipt = _read_export(path_row, source_contract, contract)
        roots.append(root)
        exports.append(export)
        receipts.append(receipt)
    if _overlaps(roots[0], roots[1]):
        raise ValueError('Namespace export roots overlap')
    run_ids, authored, seeds, known = set(), set(), set(), set()
    for export in exports:
        for values, target, label in (
                (export['historical_run_ids'], run_ids, 'run ID'),
                (export['historical_authored_ids'], authored, 'authored ID'),
                (export['training_seeds'], seeds, 'training seed'),
                (export['known_sources'], known, 'known source')):
            if target.intersection(values):
                raise ValueError(f'Namespace exports contain a duplicate {label}')
            target.update(values)
    namespace = {
        'schema': 'memory-family-namespace-inventory-v3',
        'historical_run_ids': sorted(run_ids),
        'historical_authored_ids': sorted(authored),
    }
    coverage = {
        'schema': 'memory-family-namespace-coverage-receipt-v3',
        'path_manifest': manifest,
        'coverage_contract_sha256': memory.sha256(contract),
        'known_sources': sorted(known),
        'known_sources_sha256': memory.sha256(sorted(known)),
        'training_seeds': sorted(seeds),
        'training_seeds_sha256': memory.sha256(sorted(seeds)),
        'roots': receipts,
        'searched_roots_sha256': memory.sha256(receipts),
    }
    return {'namespace': namespace, 'coverage': coverage}


def _capacity(roots):
    ordered = [_safe_absolute(roots[name], f'{name} root')
               for name in ('output', 'control', 'publication')]
    devices = set()
    for path in ordered:
        current = path
        while not current.exists():
            if current == current.parent:
                raise ValueError('Storage root has no existing ancestor')
            current = current.parent
        devices.add(current.stat().st_dev)
    if len(devices) != 1:
        raise StorageLimitError('Allocation roots must share one filesystem')
    limits = StorageLimits(
        max_bytes=ALLOCATION_MAX_BYTES, min_free_bytes=MIN_FREE_BYTES,
        max_runs=PROTOCOL['population']['max_runs'],
        max_snapshots=PROTOCOL['storage']['max_snapshots_per_run'],
        max_exports=PROTOCOL['storage']['max_exports'],
        max_entries=PROTOCOL['storage']['max_entries'])
    budget = StorageBudget(ordered, limits)
    usage = budget.usage()
    additional = max(0, ALLOCATION_MAX_BYTES - usage['used_bytes'])
    report = budget.check(additional, path=ordered[0])
    required = additional + MIN_FREE_BYTES
    return {
        'filesystem_device': next(iter(devices)),
        'used_bytes': report['used_bytes'], 'additional_bytes': additional,
        'allocation_max_bytes': ALLOCATION_MAX_BYTES,
        'free_bytes': report['free_bytes'], 'min_free_bytes': MIN_FREE_BYTES,
        'required_free_bytes': required,
        'shortfall_bytes': max(0, required - report['free_bytes']),
        'max_runs': limits.max_runs,
        'max_snapshots_per_run': limits.max_snapshots,
        'max_exports': limits.max_exports, 'max_entries': limits.max_entries,
    }


def _git_directory(repo: Path, upstream: Path) -> Path:
    def resolve(marker, label):
        if marker.is_dir() and not marker.is_symlink():
            directory = marker
        elif marker.is_file() and not marker.is_symlink():
            try:
                value = artifacts._read(marker, 4096).decode('utf-8')
            except UnicodeError as error:
                raise ValueError(f'{label} has an invalid gitdir marker') from error
            if not value.startswith('gitdir: ') or not value.endswith('\n'):
                raise ValueError(f'{label} has an invalid gitdir marker')
            raw = value[len('gitdir: '):-1]
            if not raw or '\n' in raw or '\x00' in raw:
                raise ValueError(f'{label} has an unsafe gitdir marker')
            candidate = Path(raw)
            directory = Path(os.path.abspath(
                candidate if candidate.is_absolute() else marker.parent / candidate))
        else:
            raise ValueError(f'{label} is not initialized')
        if _held_out(directory):
            raise ValueError(f'{label} cannot name held-out data')
        if any(part.is_symlink() for part in (directory, *directory.parents)):
            raise ValueError(f'{label} traverses a symlink')
        if not directory.is_dir():
            raise ValueError(f'{label} is not initialized')
        return directory

    directory = resolve(upstream / '.git', 'upstream/fly-gym gitdir')
    checkout_git = resolve(repo / '.git', 'repository Git metadata')
    expected = checkout_git / 'modules/upstream/fly-gym'
    if directory != expected:
        raise ValueError('upstream/fly-gym gitdir is outside repository Git metadata')
    return directory


def _upstream_identity(repo_root):
    repo = _safe_absolute(repo_root, 'Repository root', directory=True)
    upstream = _safe_absolute(repo / PROTOCOL['upstream']['path'],
                              'upstream/fly-gym', directory=True)
    git_directory = _git_directory(repo, upstream)
    head_path = git_directory / 'HEAD'
    if head_path.is_symlink():
        raise ValueError('upstream/fly-gym HEAD cannot be a symlink')
    try:
        head = artifacts._read(head_path, 4096).decode('ascii')
    except UnicodeError as error:
        raise ValueError('upstream/fly-gym HEAD is invalid') from error
    expected = PROTOCOL['upstream']
    if head != expected['commit'] + '\n':
        raise ValueError('upstream/fly-gym is not at the exact detached pin')
    rows, total = [], 0
    for directory, directories, files in os.walk(
            upstream, topdown=True, followlinks=False):
        current = Path(directory)
        if current == upstream:
            directories[:] = [name for name in directories if name != '.git']
            files = [name for name in files if name != '.git']
        directories.sort()
        for name in directories:
            path = current / name
            if path.is_symlink():
                raise ValueError('Pinned upstream tree contains a directory symlink')
        for name in sorted(files):
            if len(rows) >= expected['files']:
                raise ValueError('upstream/fly-gym tree exceeds the frozen file count')
            path = current / name
            relative = path.relative_to(upstream).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raw = os.readlink(path).encode()
                kind = 'symlink'
            elif stat.S_ISREG(info.st_mode):
                if total + info.st_size > expected['bytes']:
                    raise ValueError('upstream/fly-gym tree exceeds the frozen byte count')
                descriptor = _descriptor(path, label='Pinned upstream file')
                rows.append({
                    'path': relative, 'kind': 'file',
                    'executable': bool(info.st_mode & stat.S_IXUSR),
                    'bytes': descriptor['bytes'], 'sha256': descriptor['sha256'],
                })
                total += descriptor['bytes']
                continue
            else:
                raise ValueError('Pinned upstream tree contains a special file')
            if total + len(raw) > expected['bytes']:
                raise ValueError('upstream/fly-gym tree exceeds the frozen byte count')
            rows.append({
                'path': relative, 'kind': kind,
                'executable': bool(info.st_mode & stat.S_IXUSR),
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            })
            total += len(raw)
    actual = {
        'path': str(upstream), 'commit': expected['commit'],
        'files': len(rows), 'bytes': sum(row['bytes'] for row in rows),
        'inventory_sha256': memory.sha256(rows),
    }
    if {key: actual[key] for key in ('commit', 'files', 'bytes', 'inventory_sha256')} != {
            key: expected[key] for key in ('commit', 'files', 'bytes', 'inventory_sha256')}:
        raise ValueError('upstream/fly-gym tree differs from the frozen clean inventory')
    return actual


def _runtime_identity(repo_root):
    repo = _safe_absolute(repo_root, 'Repository root', directory=True)
    runtime = PROTOCOL['runtime']
    if [sys.version_info.major, sys.version_info.minor] != [
            runtime['python_major'], runtime['python_minor']]:
        raise ValueError('Python major/minor differs from allocation protocol')
    declared = Path(sys.executable)
    resolved = declared.resolve(strict=True)
    executable = _descriptor(resolved, label='Resolved Python executable')
    python = {
        'major_minor': [sys.version_info.major, sys.version_info.minor],
        'version': platform.python_version(),
        'implementation': platform.python_implementation(),
        'cache_tag': sys.implementation.cache_tag,
        'declared_executable': str(declared),
        'resolved_executable': str(resolved),
        'bytes': executable['bytes'], 'sha256': executable['sha256'],
    }
    distributions = {name: metadata.version(name)
                     for name in runtime['distributions']}
    project_files = {name: _descriptor(repo / name, label='Runtime project file')
                     for name in runtime['project_files']}
    return {'python': python, 'distributions': distributions,
            'project_files': project_files}


def _profile_identity():
    actual = {
        'family_design_sha256': memory.sha256(family_world.FAMILY_DESIGN),
        'family_profile_sha256': list(family_world.FAMILY_PROFILE_HASHES),
    }
    if actual != PROTOCOL['profile']:
        raise ValueError('Family profile identity differs from allocation protocol')
    return actual


def _behavior_identity(repo_root):
    repo = _safe_absolute(repo_root, 'Repository root', directory=True)
    result = {}
    for row in PROTOCOL['behavior_sources']:
        if (type(row) is not dict or set(row) != {'id', 'path'}
                or row['id'] in result or Path(row['path']).is_absolute()
                or '..' in Path(row['path']).parts):
            raise ValueError('Invalid behavior-source protocol entry')
        result[row['id']] = _descriptor(
            repo / row['path'], label=f"Behavior source {row['id']}")
    return result


LOADED_BEHAVIOR_IDENTITY = _behavior_identity(REPO_ROOT)


def _asset_model_identity(repo_root, asset_root):
    repo = _safe_absolute(repo_root, 'Repository root', directory=True)
    root = _safe_absolute(asset_root, 'Asset root', directory=True)
    manifest_path = repo / PROTOCOL['assets']['manifest_path']
    manifest_descriptor = _descriptor(manifest_path, label='FLYNN asset manifest')
    if manifest_descriptor['sha256'] != PROTOCOL['assets']['manifest_sha256']:
        raise ValueError('FLYNN asset manifest differs from allocation protocol')
    manifest = model_assets.load_manifest(repo)
    if manifest['profile_id'] != PROTOCOL['assets']['profile_id']:
        raise ValueError('FLYNN asset profile differs from allocation protocol')
    report = model_assets.verify_assets(repo, root)
    if not report['ok']:
        raise ValueError('Pinned FLYNN archive/checkpoint assets are missing or different')
    files = {item['id']: _descriptor(root / item['path'], label='Pinned FLYNN asset')
             for item in manifest['files']}
    archive = next(item for item in manifest['files'] if item['id'] == 'graph_archive')
    graph_root = _safe_absolute(root / f"graph-{archive['sha256']}",
                                'Prepared graph root', directory=True)
    metadata_path = graph_root / 'palimpsest-prepared.json'
    _, prepared, _ = _canonical_file(metadata_path, MiB, 'Prepared graph metadata')
    if (type(prepared) is not dict or prepared.get('archive_sha256') != archive['sha256']
            or prepared.get('upstream_commit') != manifest['upstream_commit']
            or type(prepared.get('edge_path')) is not str):
        raise ValueError('Prepared graph metadata differs')
    edge_relative = Path(prepared['edge_path'])
    if edge_relative.is_absolute() or '..' in edge_relative.parts:
        raise ValueError('Prepared graph edge must remain below the graph root')
    edge = _safe_absolute(graph_root / edge_relative,
                          'Prepared graph edge', directory=False)
    if not edge.is_relative_to(graph_root):
        raise ValueError('Prepared graph edge must remain below the graph root')
    graph = manifest['graph']
    expected_edge = graph['edge_identity']
    edge_descriptor = _descriptor(edge, label='Prepared graph edge')
    if (edge_descriptor['bytes'], edge_descriptor['sha256']) != (
            expected_edge['size_bytes'], expected_edge['sha256']):
        raise ValueError('Prepared graph edge differs')
    for item in graph['mapping_files']:
        relative = Path(item['path'])
        if (relative.is_absolute() or '..' in relative.parts
                or not (edge.parent / relative).is_relative_to(graph_root)):
            raise ValueError('Prepared graph mapping must remain below the graph root')
    model_assets._check_mappings(repo, edge.parent, graph['mapping_files'])
    mappings = {}
    for item in graph['mapping_files']:
        descriptor = _descriptor(edge.parent / item['path'], label='Prepared graph mapping')
        expected_mapping = item.get('archive_identity', item)
        if (descriptor['bytes'], descriptor['sha256']) != (
                expected_mapping['size_bytes'], expected_mapping['sha256']):
            raise ValueError('Prepared graph mapping differs')
        mappings[item['path']] = descriptor
    return {
        'manifest': manifest_descriptor,
        'assets': files,
        'model': files['checkpoint'],
        'prepared_graph': {
            'metadata': _descriptor(metadata_path, label='Prepared graph metadata'),
            'edge': edge_descriptor, 'mappings': mappings,
        },
    }


def _registration_state(source, inventory):
    path, registration, payload, digest = source
    if (registration['block'] != PROTOCOL['population']['block']
            or registration['split'] != PROTOCOL['population']['split']
            or registration['resource_projection']['known_bytes']
            != PROTOCOL['storage']['producer_subtotal_bytes']):
        raise ValueError('Producer registration differs from the allocation population')
    namespace_path = Path(registration['namespace_inventory']['path'])
    namespace = artifacts._json(artifacts._read(namespace_path, producer.MAX_NAMESPACE))
    if namespace != inventory['namespace']:
        raise ValueError('Producer namespace inventory differs from frozen coverage exports')
    _, generated = producer._plan(registration['plan']['path'], registration['block'])
    family_seeds = {case['seed'] for case in generated['cases']}
    training_seeds = set(inventory['coverage']['training_seeds'])
    if family_seeds.intersection(training_seeds):
        raise ValueError('Development family seed collides with a training seed')
    descriptor = {'path': str(path), 'bytes': len(payload), 'sha256': digest}
    return descriptor, registration


def _validated_registration(registration_path):
    """Reject held-out references before the producer opens any bound input."""
    path, value, payload = _canonical_file(
        registration_path, producer.MAX_JSON, 'Producer registration')
    if (type(value) is not dict or value.get('split') != 'development'
            or value.get('held_out_used') is not False):
        raise ValueError('Allocation requires a development-only registration')

    def check(item):
        if type(item) is str:
            if _held_out(item):
                raise ValueError('Producer registration cannot reference held-out data')
        elif type(item) is list:
            for child in item:
                check(child)
        elif type(item) is dict:
            for child in item.values():
                check(child)

    check(value)
    registration = producer.validate_registration(value)
    if path != Path(registration['roots']['publication']) / 'registration.json':
        raise ValueError('Producer registration path differs')
    return path, registration, payload, hashlib.sha256(payload).hexdigest()


def _root_state(registration, inventory, repo_root, asset_root, search_manifest,
                *, linked=False):
    roots = {name: _safe_absolute(path, f'{name} root')
             for name, path in registration['roots'].items()}
    if roots['output'].exists() or roots['control'].exists():
        raise ValueError('Output and control roots must be absent')
    if not roots['publication'].is_dir():
        raise ValueError('Publication root must already exist')
    target = roots['publication'] / 'allocation-admission.json'
    if linked:
        if not target.is_file() or target.is_symlink():
            raise RuntimeError('Exclusive admission link disappeared or changed type')
    elif target.exists() or target.is_symlink():
        raise FileExistsError(str(target))
    entries = sorted(path.name for path in roots['publication'].iterdir())
    expected_entries = (['allocation-admission.json', 'registration.json']
                        if linked else ['registration.json'])
    if entries != expected_entries:
        raise ValueError('Publication root contains an unexpected entry')
    ordered = list(roots.values())
    if any(_overlaps(left, right) for index, left in enumerate(ordered)
           for right in ordered[index + 1:]):
        raise ValueError('Allocation roots overlap')
    immutable = [
        _safe_absolute(repo_root, 'Repository root', directory=True),
        Path(os.path.abspath(asset_root)),
        _safe_absolute(search_manifest, 'Namespace path manifest', directory=False),
        *(Path(row['path']) for row in inventory['coverage']['roots']),
        Path(registration['plan']['path']), Path(registration['protocol']['path']),
        Path(registration['namespace_inventory']['path']),
        *(Path(row['path']) for row in registration['histories'].values()),
        *(Path(row['path']) for row in registration['dependencies'].values()),
    ]
    if any(_overlaps(root, source) for root in ordered for source in immutable):
        raise ValueError('Allocation root overlaps an immutable input')
    return {name: str(path) for name, path in roots.items()}, target


def _same(left, right, label):
    if memory.canonical_bytes(left) != memory.canonical_bytes(right):
        raise RuntimeError(f'{label} changed after exclusive link')


def _fsync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _inode(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError('Admission target is not a regular file')
    return info.st_dev, info.st_ino


def _durable_rollback(target, linked_inode):
    if _inode(target) != linked_inode:
        raise RuntimeError('Admission target inode changed before rollback')
    target.unlink(missing_ok=True)
    _fsync_directory(target.parent)


def _blockers(registration, search_manifest, repo_root):
    checks = (
        ('storage', lambda: _capacity(registration['roots'])),
        ('upstream', lambda: _upstream_identity(repo_root)),
        ('namespace', lambda: build_namespace_inventory(search_manifest)),
    )
    values, failures = {}, []
    for name, check in checks:
        try:
            values[name] = check()
        except (AdmissionRefused, OSError, ValueError, StorageLimitError) as error:
            failures.append(f'{name}: {error}')
    if failures:
        raise AdmissionRefused('Allocation refused: ' + '; '.join(failures))
    return values


def admit(registration_path, search_manifest_path, repo_root, asset_root):
    """Publish one receipt only for a fully resolved, zero-owner preflight."""
    registration_source = _validated_registration(registration_path)
    registration_path, registration = registration_source[:2]
    repo = _safe_absolute(repo_root, 'Repository root', directory=True)
    if repo != REPO_ROOT:
        raise ValueError('Admission checkout and --repo must match exactly')
    early = _blockers(registration, search_manifest_path, repo)
    inventory, capacity, upstream = (
        early['namespace'], early['storage'], early['upstream'])
    registration_descriptor, registration = _registration_state(
        registration_source, inventory)
    roots, target = _root_state(
        registration, inventory, repo, asset_root, search_manifest_path)
    assets_model = _asset_model_identity(repo, asset_root)
    runtime = _runtime_identity(repo)
    profile = _profile_identity()
    behavior = _behavior_identity(repo)
    _same(behavior, LOADED_BEHAVIOR_IDENTITY,
          'Behavior sources differ from executing code')
    protocol_descriptor = _descriptor(PROTOCOL_PATH, label='Allocation protocol')
    receipt = {
        'schema': 'memory-family-allocation-admission-v3',
        'scope': 'resolved-namespace-fixture-or-reviewed-contract-only',
        'storage_allocation_admitted': True,
        'allocation_authorized': True,
        'namespace_coverage_complete': True,
        'native_owner_launch_authorized': False,
        'native_allocation': False, 'held_out_used': False,
        'qualification_claims': [],
        'registration': registration_descriptor,
        'protocol': protocol_descriptor,
        'storage': capacity,
        'namespace': copy.deepcopy(inventory['coverage']),
        'identity': {
            'upstream': upstream, 'runtime': runtime, 'profile': profile,
            'assets_model': assets_model, 'behavior_sources': behavior,
        },
        'future_launcher_binding': {
            'required': True,
            'fields': ['path', 'bytes', 'sha256'],
            'native_launch_authorized_by_this_receipt': False,
        },
    }
    payload = memory.canonical_bytes(receipt)
    if len(payload) > MAX_RECEIPT:
        raise ValueError('Allocation admission exceeds its publication bound')
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    temporary, linked, linked_inode = None, False, None
    try:
        with tempfile.NamedTemporaryFile(
                mode='wb', dir=target.parent, prefix=f'.{target.name}.',
                suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
        linked = True
        linked_inode = _inode(temporary)
        if _inode(target) != linked_inode:
            raise RuntimeError('Exclusive admission link changed before validation')
        temporary.unlink()
        temporary = None

        # The exclusive final name exists before every mutable input is checked
        # again. Coverage is deliberately last so mutations caused by an earlier
        # identity check are still observed.
        current_registration, current_value = _registration_state(
            _validated_registration(registration_path), inventory)
        _same(current_registration, registration_descriptor, 'Producer registration')
        _same(current_value, registration, 'Producer registration value')
        _same(_upstream_identity(repo), upstream, 'Pinned upstream identity')
        _same(_asset_model_identity(repo, asset_root), assets_model,
              'Asset/model identity')
        _same(_runtime_identity(repo), runtime, 'Runtime identity')
        _same(_profile_identity(), profile, 'Family profile identity')
        _same(_behavior_identity(repo), behavior, 'Behavior-source identity')
        _same(_descriptor(PROTOCOL_PATH, label='Allocation protocol'),
              protocol_descriptor, 'Allocation protocol identity')
        current_capacity = _capacity(roots)
        if (current_capacity['filesystem_device'] != capacity['filesystem_device']
                or current_capacity['allocation_max_bytes'] != ALLOCATION_MAX_BYTES
                or current_capacity['min_free_bytes'] != MIN_FREE_BYTES):
            raise RuntimeError('Storage capacity identity changed after exclusive link')
        current_inventory = build_namespace_inventory(search_manifest_path)
        _same(current_inventory, inventory, 'Namespace coverage')
        current_roots, current_target = _root_state(
            registration, current_inventory, repo, asset_root,
            search_manifest_path, linked=True)
        _same(current_roots, roots, 'Allocation root identity')
        if current_target != target:
            raise RuntimeError('Allocation target changed after exclusive link')
        if _inode(target) != linked_inode:
            raise RuntimeError('Exclusive admission link inode changed before commit')
        linked_descriptor = _descriptor(target, label='Linked admission payload')
        if (linked_descriptor['bytes'] != len(payload)
                or linked_descriptor['sha256'] != payload_sha256):
            raise RuntimeError('Linked admission payload changed before commit')
        _fsync_directory(target.parent)
    except BaseException as error:
        if linked:
            try:
                _durable_rollback(target, linked_inode)
            except BaseException as rollback_error:
                raise PublicationIndeterminate(
                    'Admission rollback failed; publication state is indeterminate') \
                    from rollback_error
        raise error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'path': str(target), 'bytes': len(payload),
            'sha256': payload_sha256, 'admission': copy.deepcopy(receipt)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', required=True, type=Path)
    parser.add_argument('--search-manifest', required=True, type=Path)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    args = parser.parse_args(argv)
    result = admit(args.registration, args.search_manifest, args.repo, args.assets)
    print(memory.canonical_bytes(result).decode('utf-8'))


if __name__ == '__main__':
    main()
