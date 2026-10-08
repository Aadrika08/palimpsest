"""Finite puck-v3 layout minting and data-supplied scene admission.

Inventory discovery remains outside this module.  Admission consumes typed
snapshots and publishes only to an explicitly supplied fresh directory.
"""

import hashlib
import json
import math
import os
from pathlib import Path

from .task_mechanics import MAX_COUNTER, MAX_ITEMS


SCHEMA = 'puck-on-policy-layout-v1'
COLLECTION_SPLIT = 'on_policy_collection'
DEVELOPMENT_SPLIT = 'on_policy_development'
RESERVED_SCENE_IDS = (6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123)
HELD_OUT_SCENE_IDS = (6200, 6201, 6202, 6203, 6204, 6205, 6206, 6207)
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
_CANDIDATE_FIELDS = {'layout', 'canonical_scene', 'scientific_initial', 'payload'}
_RESERVATION_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'scene_ids', 'inventory_before_sha256',
    'inventory_after_sha256', 'inventory', 'occupied_scene_ids',
    'occupied_canonical_scene_sha256', 'occupied_scientific_initial_sha256',
    'occupied_payload_sha256',
}
_SCENE_MANIFEST_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'reservation_sha256', 'scene_ids', 'scenes',
}
_MAX_JSON_BYTES = 64 * 1024 * 1024

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


def _atomic_manifest(root, name, manifest):
    root = _publication_root(root)
    target = root / name
    pending = root / f'.{name}.pending'
    if target.exists() or target.is_symlink() or pending.exists() or pending.is_symlink():
        raise ValueError(f'{name}: fresh publication paths required')
    raw = _canonical_bytes(manifest, name)
    published = False
    try:
        with pending.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, target)
        published = True
        flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
        directory = os.open(root, flags)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            pending.unlink(missing_ok=True)
            if published:
                target.unlink(missing_ok=True)
        finally:
            raise
    return {
        'manifest_path': str(target), 'manifest_bytes': raw,
        'manifest_sha256': _sha256(raw),
    }


def _inventory_roster():
    roster = _ids(RESERVED_SCENE_IDS, 'reserved scene roster', exact_length=8)
    if set(roster) & set(HELD_OUT_SCENE_IDS):
        raise ValueError('Held-out scene IDs remain locked')
    return roster


def _validate_inventory(snapshot, lineage_sha256):
    lineage_sha256 = _digest(lineage_sha256, 'reservation lineage')
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
                occupied_ids.add(scene_id)
                for field in occupied:
                    occupied[field].add(_digest(scene[field], f'inventory {field}'))
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
    before = _validate_inventory(inventory_before, lineage_sha256)
    after = _validate_inventory(inventory_after, lineage_sha256)
    before_bytes = _canonical_bytes(inventory_before, 'inventory before')
    after_bytes = _canonical_bytes(inventory_after, 'inventory after')
    if before_bytes != after_bytes or before != after:
        raise ValueError('Inventory changed during reservation')
    roster = _inventory_roster()
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-reservation-v1',
        'lineage_sha256': lineage_sha256, 'scene_ids': list(roster),
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
    if manifest['version'] != 1 or manifest['kind'] != 'puck-on-policy-reservation-v1':
        raise ValueError('Reservation schema differs')
    lineage = _digest(manifest['lineage_sha256'], 'reservation lineage')
    if tuple(manifest['scene_ids']) != _inventory_roster():
        raise ValueError('Reservation scene roster differs')
    admitted = _validate_inventory(manifest['inventory'], lineage)
    inventory_bytes = _canonical_bytes(manifest['inventory'], 'reserved inventory')
    if (manifest['inventory_before_sha256'] != _sha256(inventory_bytes) or
            manifest['inventory_after_sha256'] != _sha256(inventory_bytes) or
            any(manifest[field] != admitted[field] for field in admitted)):
        raise ValueError('Reservation inventory binding differs')
    return manifest


def _admit_staged_layout(row, scene_id, slot, split):
    if type(row) is not dict or set(row) != _ROW_FIELDS:
        raise ValueError('Staged puck layout requires exact fields')
    if (type(row['version']) is not int or row['version'] != 1 or row['kind'] != SCHEMA or
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


def scene_candidate_identities(candidate):
    """Return independent hashes for a typed fake/real scene candidate."""
    if type(candidate) is not dict or set(candidate) != _CANDIDATE_FIELDS:
        raise ValueError('Scene candidate requires exact fields')
    result = {}
    for field, output in (
            ('canonical_scene', 'canonical_scene_sha256'),
            ('scientific_initial', 'scientific_initial_sha256'),
            ('payload', 'payload_sha256')):
        if type(candidate[field]) is not dict or not candidate[field]:
            raise ValueError(f'{field}: nonempty typed object required')
        result[output] = _sha256(_canonical_bytes(candidate[field], field))
    return result


def _read_scene_manifest(raw):
    if type(raw) is not bytes or len(raw) > _MAX_JSON_BYTES:
        raise ValueError('Canonical scene-manifest bytes required')
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Canonical scene-manifest JSON required') from error
    if (_canonical_bytes(manifest, 'scene manifest') != raw or type(manifest) is not dict or
            set(manifest) != _SCENE_MANIFEST_FIELDS or manifest['version'] != 1 or
            manifest['kind'] != 'puck-on-policy-scene-manifest-v1'):
        raise ValueError('Scene manifest schema or canonical bytes differ')
    if tuple(manifest['scene_ids']) != _inventory_roster():
        raise ValueError('Scene manifest roster differs')
    return manifest


def collection_scene_projection(scene_manifest_bytes, *, audience):
    """Derive the only view that a collection process may receive."""
    if audience != 'collection':
        raise ValueError('Only the collection scene projection is available')
    manifest = _read_scene_manifest(scene_manifest_bytes)
    collection_ids = _inventory_roster()[:4]
    scenes = manifest['scenes'][:4]
    if ([item.get('scene_id') for item in scenes] != list(collection_ids) or
            any(item.get('split') != COLLECTION_SPLIT for item in scenes)):
        raise ValueError('Collection scene projection differs')
    return _canonical_bytes({
        'version': 1, 'kind': 'puck-on-policy-collection-projection-v1',
        'lineage_sha256': manifest['lineage_sha256'],
        'reservation_sha256': manifest['reservation_sha256'],
        'scene_ids': list(collection_ids), 'scenes': scenes,
    }, 'collection projection')


def stage_scene_manifest(output_root, reservation_bytes, minter, *, inventory_after):
    """Stage all eight candidates through a caller-supplied minter and publish once."""
    if not callable(minter):
        raise ValueError('Scene minter must be callable')
    reservation = _read_reservation(reservation_bytes)
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
        candidate = minter(scene_id, slot, split)
        if type(candidate) is not dict or set(candidate) != _CANDIDATE_FIELDS:
            raise ValueError('Scene minter returned an invalid candidate')
        _admit_staged_layout(candidate['layout'], scene_id, slot, split)
        identities = scene_candidate_identities(candidate)
        for field, value in identities.items():
            if value in occupied[field]:
                raise ValueError(f'{field} collision')
        normalized = json.loads(_canonical_bytes(candidate, 'scene candidate'))
        scenes.append({
            'scene_id': scene_id, 'slot': slot, 'split': split,
            **identities, 'candidate': normalized,
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
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-scene-manifest-v1',
        'lineage_sha256': reservation['lineage_sha256'],
        'reservation_sha256': _sha256(reservation_bytes),
        'scene_ids': list(roster), 'scenes': scenes,
    }
    manifest_bytes = _canonical_bytes(manifest, 'scene manifest')
    projection = collection_scene_projection(manifest_bytes, audience='collection')
    result = _atomic_manifest(output_root, 'scene-manifest.json', manifest)
    result['collection_projection_bytes'] = projection
    return result
