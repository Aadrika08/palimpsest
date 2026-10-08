"""Finite puck-v3 layout minting and data-supplied scene admission.

Inventory discovery remains outside this module.  Admission consumes typed
snapshots and publishes only to an explicitly supplied fresh directory.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import stat

from .task_mechanics import MAX_COUNTER, MAX_ITEMS


SCHEMA = 'puck-on-policy-layout-v1'
COLLECTION_SPLIT = 'on_policy_collection'
DEVELOPMENT_SPLIT = 'on_policy_development'
RESERVED_SCENE_IDS = (6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123)
HELD_OUT_SCENE_IDS = (6200, 6201, 6202, 6203, 6204, 6205, 6206, 6207)
PROTOCOL_SHA256 = 'fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13'
_ROW_FIELDS = {'version', 'kind', 'seed', 'split', 'slot', 'rover_pose',
               'puck_xy', 'goal_xy', 'initial_qvel'}
_INVENTORY_KINDS = {'ref', 'worktree', 'raw_registry', 'manifest'}
_ROOT_FIELDS = {'kind', 'path', 'resolved_path', 'exists', 'readable',
                'is_directory', 'is_symlink', 'identity_sha256'}
_RECORD_FIELDS = {'kind', 'name', 'root', 'identity_sha256', 'role',
                  'lineage_sha256', 'scenes', 'metadata'}
_SCENE_FIELDS = {'scene_id', 'canonical_scene_sha256',
                 'scientific_initial_sha256', 'payload_sha256'}
_INVENTORY_FIELDS = {'version', 'complete', 'remote_refs_fresh',
                     'held_out_accessed', 'roots', 'records'}
_RESERVATION_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'scene_ids', 'inventory_before_sha256',
    'inventory_after_sha256', 'inventory', 'occupied_scene_ids',
    'occupied_canonical_scene_sha256', 'occupied_scientific_initial_sha256',
    'occupied_payload_sha256',
}
_SCENE_MANIFEST_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'reservation_sha256', 'scene_ids', 'scenes',
}
_SCENE_ENTRY_FIELDS = {
    'scene_id', 'slot', 'split', 'canonical_scene_sha256',
    'scientific_initial_sha256', 'payload_sha256', 'layout',
}
_COMMIT_RECEIPT_FIELDS = {
    'version', 'kind', 'target', 'manifest_sha256', 'manifest_bytes',
    'reservation_sha256', 'protocol_sha256',
}
_MAX_JSON_BYTES = 64 * 1024 * 1024
_MAX_COMMIT_BYTES = 4096

# Integer eighth-metre/radian coefficients.  Fixed slots 0..7 are the complete
# parameter domain; binary-fraction conversion makes the arithmetic exact.
# Fields: puck x/y, goal dx/dy, rover dx/dy, rover yaw.
_PARAMETER_DOMAIN = (
    (-4, -4, 8, 0, -6, -2, 2),
    (-4, -2, 10, 2, -7, 2, -2),
    (-4, 2, 12, -2, -8, -2, 3),
    (-4, 4, 14, 0, -6, 2, -3),
    (-2, -4, 9, 1, -7, -2, 4),
    (-2, -2, 11, -1, -8, 2, -4),
    (-2, 2, 13, 1, -6, -2, 1),
    (-2, 4, 15, -1, -7, 2, -1),
)


def _ids(values, label, *, exact_length=None):
    if type(values) not in (list, tuple) or len(values) > MAX_ITEMS:
        raise ValueError(f'{label}: bounded list/tuple required')
    if exact_length is not None and len(values) != exact_length:
        raise ValueError(f'{label}: exactly {exact_length} IDs required')
    if any(type(value) is not int or not 0 <= value <= MAX_COUNTER for value in values):
        raise ValueError(f'{label}: bounded integer IDs required')
    if list(values) != sorted(values) or len(set(values)) != len(values):
        raise ValueError(f'{label}: unique increasing IDs required')
    return tuple(values)


def _row(seed, slot):
    px, py, gx, gy, rx, ry, yaw = _PARAMETER_DOMAIN[slot]
    puck = [px / 8, py / 8]
    return {
        'version': 1,
        'kind': SCHEMA,
        'seed': seed,
        'split': COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT,
        'slot': slot,
        'rover_pose': [(px + rx) / 8, (py + ry) / 8, yaw / 8],
        'puck_xy': puck,
        'goal_xy': [(px + gx) / 8, (py + gy) / 8],
        'initial_qvel': 'all zeros',
    }


def mint_layouts(scene_ids, *, occupied_scene_ids=()):
    """Return the eight fixed layouts for nonreserved synthetic IDs only."""
    scene_ids = _ids(scene_ids, 'scene domain', exact_length=len(_PARAMETER_DOMAIN))
    occupied = _ids(occupied_scene_ids, 'occupied scene IDs')
    if set(scene_ids) & set(RESERVED_SCENE_IDS):
        raise ValueError('Reserved puck scene IDs remain locked')
    if set(scene_ids) & set(occupied):
        raise ValueError('Puck scene ID collision')
    return [_row(seed, slot) for slot, seed in enumerate(scene_ids)]


def admit_layout(row, *, seed, split):
    """Validate one exact minter row for the explicit-layout reset seam."""
    (seed,) = _ids([seed], 'explicit layout seed', exact_length=1)
    if seed in RESERVED_SCENE_IDS:
        raise ValueError('Reserved puck scene IDs remain locked')
    if split not in (COLLECTION_SPLIT, DEVELOPMENT_SPLIT):
        raise ValueError('Explicit puck layout split differs')
    if type(row) is not dict or set(row) != _ROW_FIELDS:
        raise ValueError('Explicit puck layout requires exact fields')
    if (type(row['version']) is not int or type(row['seed']) is not int or
            type(row['slot']) is not int or type(row['kind']) is not str or
            type(row['split']) is not str or type(row['initial_qvel']) is not str or
            any(type(row[key]) is not list for key in ('rover_pose', 'puck_xy', 'goal_xy')) or
            any(type(value) is not float for key in ('rover_pose', 'puck_xy', 'goal_xy')
                for value in row[key])):
        raise ValueError('Explicit puck layout JSON types differ')
    slot = row['slot']
    expected = _row(seed, slot) if 0 <= slot < len(_PARAMETER_DOMAIN) else None
    exact_floats = expected is not None and all(
        [value.hex() for value in row[key]] == [value.hex() for value in expected[key]]
        for key in ('rover_pose', 'puck_xy', 'goal_xy'))
    if expected is None or row != expected or not exact_floats or row['split'] != split:
        raise ValueError('Explicit puck layout differs from fixed mapping')
    return expected


def _canonical_bytes(value, label):
    try:
        raw = json.dumps(value, allow_nan=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8') + b'\n'
    except (TypeError, ValueError) as error:
        raise ValueError(f'{label}: canonical JSON required') from error
    if len(raw) > _MAX_JSON_BYTES:
        raise ValueError(f'{label}: JSON exceeds bound')
    return raw


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value, label):
    if (type(value) is not str or len(value) != 64 or
            any(character not in '0123456789abcdef' for character in value)):
        raise ValueError(f'{label}: lowercase SHA-256 required')
    return value


def _publication_root(value):
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError('Publication root path required')
    root = Path(value)
    if (not root.is_absolute() or not root.exists() or not root.is_dir() or
            root.is_symlink() or root.resolve(strict=True) != root):
        raise ValueError('Publication root must be an exact existing directory')
    return root


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _directory_identity(value):
    return value.st_dev, value.st_ino, value.st_mode


def _object_identity(value):
    return value.st_dev, value.st_ino, value.st_mode, value.st_nlink


def _fsync_directory(root):
    root = _publication_root(root)
    before = os.lstat(root)
    flags = (os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) |
             getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    directory = os.open(root, flags)
    try:
        opened = os.fstat(directory)
        rebound = os.lstat(root)
        if (not stat.S_ISDIR(opened.st_mode) or
                _directory_identity(opened) != _directory_identity(before) or
                _directory_identity(opened) != _directory_identity(rebound)):
            raise ValueError('Publication parent directory rebound')
        os.fsync(directory)
        after = os.fstat(directory)
        rebound = os.lstat(root)
        if (_directory_identity(after) != _directory_identity(opened) or
                _directory_identity(rebound) != _directory_identity(opened)):
            raise ValueError('Publication parent directory changed during fsync')
    finally:
        os.close(directory)


def _path_present(path):
    return os.path.lexists(os.fspath(path))


def _write_bytes_new(path, raw, maximum):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError('Bounded publication bytes required')
    path = Path(path)
    root = _publication_root(path.parent)
    if path.parent != root or not path.name:
        raise ValueError('Publication file parent differs')
    root_before = os.lstat(root)
    root_flags = (os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) |
                  getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    root_descriptor = os.open(root, root_flags)
    descriptor = None
    try:
        root_opened = os.fstat(root_descriptor)
        if (not stat.S_ISDIR(root_opened.st_mode) or
                _directory_identity(root_opened) != _directory_identity(root_before) or
                _directory_identity(os.lstat(root)) != _directory_identity(root_opened)):
            raise ValueError('Publication parent directory rebound')
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
        descriptor = os.open(path.name, flags, 0o600, dir_fd=root_descriptor)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ValueError('New publication file is linked or nonregular')
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError('Short publication write')
            view = view[written:]
        os.fsync(descriptor)
        after = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=root_descriptor, follow_symlinks=False)
        if (_object_identity(after) != _object_identity(opened) or
                _identity(rebound) != _identity(after) or
                after.st_nlink != 1 or after.st_size != len(raw)):
            raise ValueError('Publication file rebound during write')
        root_after = os.fstat(root_descriptor)
        if (_directory_identity(root_after) != _directory_identity(root_opened) or
                _directory_identity(os.lstat(root)) != _directory_identity(root_opened)):
            raise ValueError('Publication parent changed during write')
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(root_descriptor)


def _read_exact_file(root, path, maximum, label):
    root = _publication_root(root)
    path = Path(path)
    if path.parent != root or not path.name:
        raise ValueError(f'{label}: exact parent required')
    root_before = os.lstat(root)
    root_flags = (os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) |
                  getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    root_descriptor = os.open(root, root_flags)
    descriptor = None
    try:
        root_opened = os.fstat(root_descriptor)
        if (not stat.S_ISDIR(root_opened.st_mode) or
                _directory_identity(root_opened) != _directory_identity(root_before) or
                _directory_identity(os.lstat(root)) != _directory_identity(root_opened)):
            raise ValueError(f'{label}: parent directory rebound')
        before = os.stat(path.name, dir_fd=root_descriptor, follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                before.st_size > maximum):
            raise ValueError(f'{label}: missing, linked, or oversized file')
        flags = (os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) |
                 getattr(os, 'O_CLOEXEC', 0))
        descriptor = os.open(path.name, flags, dir_fd=root_descriptor)
        opened = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=root_descriptor, follow_symlinks=False)
        if (_identity(opened) != _identity(before) or
                _identity(rebound) != _identity(opened)):
            raise ValueError(f'{label}: file rebound while opening')
        chunks = []
        remaining = maximum + 1
        while remaining:
            block = os.read(descriptor, min(65536, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=root_descriptor, follow_symlinks=False)
        root_after = os.fstat(root_descriptor)
        if (len(raw) > maximum or _identity(after) != _identity(opened) or
                _identity(rebound) != _identity(opened)):
            raise ValueError(f'{label}: file changed during read')
        if (_directory_identity(root_after) != _directory_identity(root_opened) or
                _directory_identity(os.lstat(root)) != _directory_identity(root_opened)):
            raise ValueError(f'{label}: parent directory changed during read')
        return raw
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(root_descriptor)


def _quarantine_path(root, name):
    return root / f'.{name}.quarantine'


def _commit_path(root, name):
    return root / f'{name}.commit.json'


def _commit_pending_path(root, name):
    return root / f'.{name}.commit.pending'


def _publication_paths(root, name):
    return {
        'target': root / name,
        'pending': root / f'.{name}.pending',
        'quarantine': _quarantine_path(root, name),
        'commit': _commit_path(root, name),
        'commit_pending': _commit_pending_path(root, name),
    }


def _fresh_publication_root(value, name):
    root = _publication_root(value)
    paths = _publication_paths(root, name)
    if any(_path_present(path) for path in paths.values()):
        raise ValueError(f'{name}: fresh publication paths required')
    return root


def _write_quarantine(root, name):
    quarantine = _quarantine_path(root, name)
    marker = _canonical_bytes({
        'version': 1, 'kind': 'puck-on-policy-publication-quarantine-v1',
        'target': name,
    }, 'publication quarantine')
    _write_bytes_new(quarantine, marker, _MAX_COMMIT_BYTES)
    _fsync_directory(root)
    return quarantine


def _commit_receipt(name, manifest, raw):
    if type(manifest) is not dict:
        raise ValueError('Publication manifest must be an object')
    lineage_sha256 = _digest(manifest.get('lineage_sha256'),
                             'publication protocol')
    if lineage_sha256 != PROTOCOL_SHA256:
        raise ValueError('Publication protocol lineage differs')
    if name == 'reservation.json':
        if manifest.get('kind') != 'puck-on-policy-reservation-v1':
            raise ValueError('Reservation publication kind differs')
        reservation_sha256 = _sha256(raw)
    elif name == 'scene-manifest.json':
        if manifest.get('kind') != 'puck-on-policy-scene-manifest-v1':
            raise ValueError('Scene publication kind differs')
        reservation_sha256 = _digest(
            manifest.get('reservation_sha256'), 'publication reservation')
    else:
        raise ValueError('Unsupported publication target')
    return {
        'version': 1,
        'kind': 'puck-on-policy-publication-commit-v1',
        'target': name,
        'manifest_sha256': _sha256(raw),
        'manifest_bytes': len(raw),
        'reservation_sha256': reservation_sha256,
        'protocol_sha256': PROTOCOL_SHA256,
    }


def _write_commit_receipt(path, raw):
    _write_bytes_new(path, raw, _MAX_COMMIT_BYTES)


def _exclusive_publish(pending, final):
    pending, final = Path(pending), Path(final)
    if pending.parent != final.parent:
        raise ValueError('Publication names must share one exact parent')
    if _path_present(final):
        raise FileExistsError(f'Publication destination exists: {final.name}')
    os.link(pending, final, follow_symlinks=False)
    source = os.lstat(pending)
    destination = os.lstat(final)
    if (not stat.S_ISREG(source.st_mode) or
            (source.st_dev, source.st_ino) != (destination.st_dev, destination.st_ino) or
            source.st_nlink != 2 or destination.st_nlink != 2):
        raise ValueError('Exclusive publication link identity differs')


def _atomic_manifest(root, name, manifest):
    root = _fresh_publication_root(root, name)
    paths = _publication_paths(root, name)
    target, pending = paths['target'], paths['pending']
    quarantine = paths['quarantine']
    commit, commit_pending = paths['commit'], paths['commit_pending']
    raw = _canonical_bytes(manifest, name)
    commit_raw = _canonical_bytes(
        _commit_receipt(name, manifest, raw), 'publication commit receipt')
    _write_bytes_new(pending, raw, _MAX_JSON_BYTES)
    _write_quarantine(root, name)
    _exclusive_publish(pending, target)
    _fsync_directory(root)
    pending.unlink()
    _fsync_directory(root)
    _write_commit_receipt(commit_pending, commit_raw)
    _exclusive_publish(commit_pending, commit)
    _fsync_directory(root)
    commit_pending.unlink()
    _fsync_directory(root)
    if (_read_exact_file(root, target, _MAX_JSON_BYTES, name) != raw or
            _read_exact_file(root, commit, _MAX_COMMIT_BYTES,
                             'publication commit receipt') != commit_raw):
        raise ValueError('Durable publication bytes changed before commit')
    result = {
        'manifest_path': str(target), 'manifest_bytes': raw,
        'manifest_sha256': _sha256(raw),
        'commit_path': str(commit), 'commit_bytes': commit_raw,
        'commit_sha256': _sha256(commit_raw),
    }
    # The target and positive receipt are already durably linked.  This unlink is
    # the commit point and intentionally has no later fallible syscall.  A crash
    # may restore the un-fsynced quarantine entry, which fails closed.
    quarantine.unlink()
    return result


def _read_publication(value, name):
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError(f'{name}: publication path required')
    target = Path(value)
    if not target.is_absolute() or target.name != name:
        raise ValueError(f'{name}: exact publication path required')
    root = _publication_root(target.parent)
    paths = _publication_paths(root, name)
    pending, quarantine = paths['pending'], paths['quarantine']
    commit, commit_pending = paths['commit'], paths['commit_pending']
    if any(_path_present(path) for path in (quarantine, pending, commit_pending)):
        raise ValueError(f'{name}: publication is quarantined or indeterminate')
    try:
        raw = _read_exact_file(root, target, _MAX_JSON_BYTES, name)
        commit_raw = _read_exact_file(root, commit, _MAX_COMMIT_BYTES,
                                      'publication commit receipt')
    except OSError as error:
        raise ValueError(f'{name}: exact target and commit receipt required') from error
    if any(_path_present(path) for path in (quarantine, pending, commit_pending)):
        raise ValueError(f'{name}: publication changed while read')
    try:
        manifest = json.loads(raw)
        receipt = json.loads(commit_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f'{name}: publication or commit JSON differs') from error
    expected = _commit_receipt(name, manifest, raw)
    if (type(receipt) is not dict or set(receipt) != _COMMIT_RECEIPT_FIELDS or
            _canonical_bytes(receipt, 'publication commit receipt') != commit_raw or
            type(receipt['version']) is not int or
            type(receipt['manifest_bytes']) is not int or
            receipt != expected):
        raise ValueError(f'{name}: positive commit receipt differs')
    try:
        if _read_exact_file(root, target, _MAX_JSON_BYTES, name) != raw:
            raise ValueError(f'{name}: publication changed after commit admission')
        if _read_exact_file(root, commit, _MAX_COMMIT_BYTES,
                            'publication commit receipt') != commit_raw:
            raise ValueError(f'{name}: commit receipt changed during admission')
    except OSError as error:
        raise ValueError(f'{name}: publication disappeared during admission') from error
    if any(_path_present(path) for path in (quarantine, pending, commit_pending)):
        raise ValueError(f'{name}: publication changed during final admission')
    return raw


def _inventory_roster():
    roster = _ids(RESERVED_SCENE_IDS, 'reserved scene roster', exact_length=8)
    if set(roster) & set(HELD_OUT_SCENE_IDS):
        raise ValueError('Held-out scene IDs remain locked')
    return roster


def _validate_inventory(snapshot, lineage_sha256):
    lineage_sha256 = _digest(lineage_sha256, 'reservation lineage')
    if lineage_sha256 != PROTOCOL_SHA256:
        raise ValueError('Reservation lineage differs from frozen protocol')
    if type(snapshot) is not dict or set(snapshot) != _INVENTORY_FIELDS:
        raise ValueError('Inventory snapshot requires exact fields')
    if (type(snapshot['version']) is not int or snapshot['version'] != 1 or
            type(snapshot['complete']) is not bool or not snapshot['complete'] or
            type(snapshot['remote_refs_fresh']) is not bool or
            not snapshot['remote_refs_fresh'] or
            type(snapshot['held_out_accessed']) is not bool or
            snapshot['held_out_accessed']):
        raise ValueError('Inventory snapshot is incomplete, stale, or accessed held-out')
    roots, records = snapshot['roots'], snapshot['records']
    if (type(roots) is not list or not roots or len(roots) > MAX_ITEMS or
            type(records) is not list or not records or len(records) > MAX_ITEMS):
        raise ValueError('Inventory roots and records must be bounded lists')

    root_kinds = set()
    root_paths = {}
    resolved_paths = set()
    for root in roots:
        if type(root) is not dict or set(root) != _ROOT_FIELDS:
            raise ValueError('Inventory root requires exact fields')
        kind, path, resolved = root['kind'], root['path'], root['resolved_path']
        if kind not in _INVENTORY_KINDS:
            raise ValueError('Inventory root kind differs')
        if (type(path) is not str or type(resolved) is not str or
                not Path(path).is_absolute() or path != os.path.normpath(path) or
                path != resolved or resolved in resolved_paths):
            raise ValueError('Inventory root path is aliased')
        for field in ('exists', 'readable', 'is_directory', 'is_symlink'):
            if type(root[field]) is not bool:
                raise ValueError('Inventory root flags must be booleans')
        if (not root['exists'] or not root['readable'] or not root['is_directory'] or
                root['is_symlink']):
            raise ValueError('Inventory root is missing, unreadable, or symlinked')
        _digest(root['identity_sha256'], 'inventory root identity')
        root_kinds.add(kind)
        root_paths[path] = kind
        resolved_paths.add(resolved)
    if root_kinds != _INVENTORY_KINDS:
        raise ValueError('Inventory root roster is incomplete')

    roster = _inventory_roster()
    self_reservations = []
    occupied_ids = set()
    occupied = {field: set() for field in (
        'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')}
    record_names = set()
    record_kinds = set()
    for record in records:
        if type(record) is not dict or set(record) != _RECORD_FIELDS:
            raise ValueError('Inventory record requires exact fields')
        kind, name, root = record['kind'], record['name'], record['root']
        if (kind not in _INVENTORY_KINDS or type(name) is not str or not name or
                len(name) > 256 or (kind, name) in record_names or
                root_paths.get(root) != kind):
            raise ValueError('Inventory record identity or root differs')
        _digest(record['identity_sha256'], 'inventory record identity')
        if len(_canonical_bytes(record['metadata'], 'inventory metadata')) > 65536:
            raise ValueError('Inventory metadata exceeds bound')
        scenes = record['scenes']
        if type(scenes) is not list or len(scenes) > MAX_ITEMS:
            raise ValueError('Inventory record scenes must be a bounded list')
        role = record['role']
        if role == 'prior':
            if record['lineage_sha256'] is not None:
                raise ValueError('Prior record cannot share reservation lineage')
        elif role == 'self_reservation':
            if record['lineage_sha256'] != lineage_sha256:
                raise ValueError('Self reservation lineage differs')
            self_reservations.append(record)
        else:
            raise ValueError('Inventory record role differs')
        scene_ids = []
        for scene in scenes:
            if type(scene) is not dict or set(scene) != _SCENE_FIELDS:
                raise ValueError('Inventory scene requires exact typed fields')
            (scene_id,) = _ids([scene['scene_id']], 'inventory scene ID', exact_length=1)
            scene_ids.append(scene_id)
            if role == 'self_reservation':
                if any(scene[field] is not None for field in occupied):
                    raise ValueError('Unminted self reservation carries identities')
            else:
                if scene_id in roster:
                    raise ValueError('Reserved puck scene ID collision')
                identities = {
                    field: _digest(scene[field], f'inventory {field}')
                    for field in occupied}
                if (scene_id in occupied_ids or
                        any(value in occupied[field]
                            for field, value in identities.items())):
                    raise ValueError('Prior puck scene or identity collision')
                occupied_ids.add(scene_id)
                for field in occupied:
                    occupied[field].add(identities[field])
        if role == 'self_reservation' and tuple(scene_ids) != roster:
            raise ValueError('Self reservation roster is partial or reordered')
        record_names.add((kind, name))
        record_kinds.add(kind)
    if record_kinds != _INVENTORY_KINDS or len(self_reservations) != 1:
        raise ValueError('Inventory records or self reservation lineage are incomplete')
    return {
        'occupied_scene_ids': sorted(occupied_ids),
        'occupied_canonical_scene_sha256': sorted(occupied['canonical_scene_sha256']),
        'occupied_scientific_initial_sha256': sorted(occupied['scientific_initial_sha256']),
        'occupied_payload_sha256': sorted(occupied['payload_sha256']),
    }


def reserve_scene_roster(output_root, inventory_before, inventory_after, *, lineage_sha256):
    """Admit supplied inventory snapshots and atomically reserve all eight IDs."""
    output_root = _fresh_publication_root(output_root, 'reservation.json')
    before = _validate_inventory(inventory_before, lineage_sha256)
    after = _validate_inventory(inventory_after, lineage_sha256)
    before_bytes = _canonical_bytes(inventory_before, 'inventory before')
    after_bytes = _canonical_bytes(inventory_after, 'inventory after')
    if before_bytes != after_bytes or before != after:
        raise ValueError('Inventory changed during reservation')
    roster = _inventory_roster()
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-reservation-v1',
        'lineage_sha256': PROTOCOL_SHA256, 'scene_ids': list(roster),
        'inventory_before_sha256': _sha256(before_bytes),
        'inventory_after_sha256': _sha256(after_bytes),
        'inventory': json.loads(before_bytes),
        **before,
    }
    return _atomic_manifest(output_root, 'reservation.json', manifest)


def _read_reservation(raw):
    if type(raw) is not bytes or len(raw) > _MAX_JSON_BYTES:
        raise ValueError('Canonical reservation bytes required')
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Canonical reservation JSON required') from error
    if _canonical_bytes(manifest, 'reservation') != raw:
        raise ValueError('Reservation bytes are not canonical')
    if type(manifest) is not dict or set(manifest) != _RESERVATION_FIELDS:
        raise ValueError('Reservation manifest requires exact fields')
    if (type(manifest['version']) is not int or manifest['version'] != 1 or
            manifest['kind'] != 'puck-on-policy-reservation-v1'):
        raise ValueError('Reservation schema differs')
    lineage = _digest(manifest['lineage_sha256'], 'reservation lineage')
    if lineage != PROTOCOL_SHA256:
        raise ValueError('Reservation lineage differs from frozen protocol')
    if tuple(manifest['scene_ids']) != _inventory_roster():
        raise ValueError('Reservation scene roster differs')
    admitted = _validate_inventory(manifest['inventory'], lineage)
    inventory_bytes = _canonical_bytes(manifest['inventory'], 'reserved inventory')
    if (manifest['inventory_before_sha256'] != _sha256(inventory_bytes) or
            manifest['inventory_after_sha256'] != _sha256(inventory_bytes) or
            any(manifest[field] != admitted[field] for field in admitted)):
        raise ValueError('Reservation inventory binding differs')
    return manifest


def _read_published_reservation(path):
    raw = _read_publication(path, 'reservation.json')
    return raw, _read_reservation(raw)


def _admit_staged_layout(row, scene_id, slot, split):
    if type(row) is not dict or set(row) != _ROW_FIELDS:
        raise ValueError('Staged puck layout requires exact fields')
    if (type(scene_id) is not int or type(slot) is not int or
            not 0 <= slot < 8 or
            split != (COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT) or
            type(row['version']) is not int or row['version'] != 1 or row['kind'] != SCHEMA or
            type(row['seed']) is not int or row['seed'] != scene_id or
            type(row['slot']) is not int or row['slot'] != slot or row['split'] != split or
            row['initial_qvel'] != 'all zeros'):
        raise ValueError('Staged puck layout identity differs')
    sizes = {'rover_pose': 3, 'puck_xy': 2, 'goal_xy': 2}
    for field, size in sizes.items():
        values = row[field]
        if (type(values) is not list or len(values) != size or
                any(type(value) is not float or not math.isfinite(value) or
                    (value == 0 and math.copysign(1, value) < 0) for value in values)):
            raise ValueError('Staged puck layout JSON numbers differ')
    coordinates = row['rover_pose'][:2] + row['puck_xy'] + row['goal_xy']
    if (max(map(abs, coordinates)) > 5 or abs(row['rover_pose'][2]) > math.pi or
            math.dist(row['rover_pose'][:2], row['puck_xy']) <= .55 or
            math.dist(row['puck_xy'], row['goal_xy']) <= .99):
        raise ValueError('Staged puck layout violates task-v5 bounds or clearance')


def scene_candidate_identities(layout):
    """Derive all collision identities from one admitted exact layout."""
    if type(layout) is not dict or set(layout) != _ROW_FIELDS:
        raise ValueError('Scene layout requires exact fields')
    scene_id, slot, split = layout['seed'], layout['slot'], layout['split']
    _admit_staged_layout(layout, scene_id, slot, split)
    canonical_scene = {
        'version': 1, 'kind': 'puck-on-policy-canonical-scene-v1',
        'rover_pose': layout['rover_pose'], 'puck_xy': layout['puck_xy'],
        'goal_xy': layout['goal_xy'],
    }
    scientific_initial = canonical_scene | {
        'kind': 'puck-on-policy-scientific-initial-v1',
        'initial_qvel': layout['initial_qvel'],
    }
    return {
        'canonical_scene_sha256': _sha256(
            _canonical_bytes(canonical_scene, 'canonical scene')),
        'scientific_initial_sha256': _sha256(
            _canonical_bytes(scientific_initial, 'scientific initial')),
        'payload_sha256': _sha256(_canonical_bytes(layout, 'complete scene payload')),
    }


def _validate_scene_entry(entry, scene_id, slot, split):
    if type(entry) is not dict or set(entry) != _SCENE_ENTRY_FIELDS:
        raise ValueError('Scene-manifest entry requires exact fields')
    if (type(entry['scene_id']) is not int or entry['scene_id'] != scene_id or
            type(entry['slot']) is not int or entry['slot'] != slot or
            entry['split'] != split):
        raise ValueError('Scene-manifest entry order or identity differs')
    _admit_staged_layout(entry['layout'], scene_id, slot, split)
    identities = scene_candidate_identities(entry['layout'])
    for field, expected in identities.items():
        if _digest(entry[field], f'scene manifest {field}') != expected:
            raise ValueError(f'Scene-manifest {field} is unbound')
    return identities


def _read_scene_manifest(raw, reservation_raw):
    if type(raw) is not bytes or len(raw) > _MAX_JSON_BYTES:
        raise ValueError('Canonical scene-manifest bytes required')
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Canonical scene-manifest JSON required') from error
    if (type(manifest) is not dict or
            _canonical_bytes(manifest, 'scene manifest') != raw or
            set(manifest) != _SCENE_MANIFEST_FIELDS or
            type(manifest['version']) is not int or manifest['version'] != 1 or
            manifest['kind'] != 'puck-on-policy-scene-manifest-v1'):
        raise ValueError('Scene manifest schema or canonical bytes differ')
    reservation = _read_reservation(reservation_raw)
    if (_digest(manifest['lineage_sha256'], 'scene-manifest lineage') !=
            reservation['lineage_sha256'] or
            _digest(manifest['reservation_sha256'], 'scene-manifest reservation') !=
            _sha256(reservation_raw)):
        raise ValueError('Scene manifest reservation lineage is unbound')
    roster = _inventory_roster()
    if tuple(manifest['scene_ids']) != roster:
        raise ValueError('Scene manifest roster differs')
    scenes = manifest['scenes']
    if type(scenes) is not list or len(scenes) != len(roster):
        raise ValueError('Scene manifest requires exactly eight entries')
    occupied_ids = set(reservation['occupied_scene_ids'])
    seen_ids = set()
    seen = {
        field: set(reservation[f'occupied_{field}']) for field in (
            'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
    }
    for slot, (scene_id, entry) in enumerate(zip(roster, scenes)):
        split = COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT
        if scene_id in occupied_ids or scene_id in seen_ids:
            raise ValueError('Scene-manifest scene ID collision')
        identities = _validate_scene_entry(entry, scene_id, slot, split)
        if any(value in seen[field] for field, value in identities.items()):
            raise ValueError('Scene-manifest identity collision')
        seen_ids.add(scene_id)
        for field, value in identities.items():
            seen[field].add(value)
    return manifest


def _collection_projection_bytes(manifest):
    collection_ids = _inventory_roster()[:4]
    scenes = [{field: entry[field] for field in _SCENE_ENTRY_FIELDS}
              for entry in manifest['scenes'][:4]]
    return _canonical_bytes({
        'version': 1, 'kind': 'puck-on-policy-collection-projection-v1',
        'scene_ids': list(collection_ids), 'scenes': scenes,
    }, 'collection projection')


def collection_scene_projection(scene_manifest_path, *, reservation_path, audience):
    """Read durable publications and derive the only collection-visible view."""
    if audience != 'collection':
        raise ValueError('Only the collection scene projection is available')
    reservation_raw, _ = _read_published_reservation(reservation_path)
    scene_raw = _read_publication(scene_manifest_path, 'scene-manifest.json')
    manifest = _read_scene_manifest(scene_raw, reservation_raw)
    if _read_publication(reservation_path, 'reservation.json') != reservation_raw:
        raise ValueError('Reservation changed while deriving collection projection')
    return _collection_projection_bytes(manifest)


def stage_scene_manifest(output_root, reservation_path, minter, *, inventory_after):
    """Stage all eight candidates through a caller-supplied minter and publish once."""
    output_root = _fresh_publication_root(output_root, 'scene-manifest.json')
    if not callable(minter):
        raise ValueError('Scene minter must be callable')
    reservation_raw, reservation = _read_published_reservation(reservation_path)
    roster = _inventory_roster()
    occupied_ids = set(reservation['occupied_scene_ids'])
    seen_ids = set()
    occupied = {
        field: set(reservation[f'occupied_{field}']) for field in (
            'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
    }
    scenes = []
    for slot, scene_id in enumerate(roster):
        split = COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT
        if scene_id in occupied_ids or scene_id in seen_ids:
            raise ValueError('Puck scene ID collision')
        layout = minter(scene_id, slot, split)
        _admit_staged_layout(layout, scene_id, slot, split)
        identities = scene_candidate_identities(layout)
        for field, value in identities.items():
            if value in occupied[field]:
                raise ValueError(f'{field} collision')
        normalized = json.loads(_canonical_bytes(layout, 'scene layout'))
        scenes.append({
            'scene_id': scene_id, 'slot': slot, 'split': split,
            **identities, 'layout': normalized,
        })
        seen_ids.add(scene_id)
        for field, value in identities.items():
            occupied[field].add(value)

    final = _validate_inventory(inventory_after, reservation['lineage_sha256'])
    final_bytes = _canonical_bytes(inventory_after, 'final inventory')
    if (final_bytes != _canonical_bytes(reservation['inventory'], 'reserved inventory') or
            _sha256(final_bytes) != reservation['inventory_after_sha256'] or
            any(final[field] != reservation[field] for field in final)):
        raise ValueError('Inventory changed before scene publication')
    if _read_publication(reservation_path, 'reservation.json') != reservation_raw:
        raise ValueError('Reservation changed before scene publication')
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-scene-manifest-v1',
        'lineage_sha256': reservation['lineage_sha256'],
        'reservation_sha256': _sha256(reservation_raw),
        'scene_ids': list(roster), 'scenes': scenes,
    }
    manifest_bytes = _canonical_bytes(manifest, 'scene manifest')
    _read_scene_manifest(manifest_bytes, reservation_raw)
    projection = _collection_projection_bytes(manifest)
    result = _atomic_manifest(output_root, 'scene-manifest.json', manifest)
    result['collection_projection_bytes'] = projection
    return result
