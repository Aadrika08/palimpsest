"""Pure registry document identities and declared dependencies.

Supplied inventory flags and publication stat tuples are historical declarations.
Layout binding authenticates only the hash domains of supplied canonical bytes;
this module opens no files and grants no inventory, collection or native authority.
"""
import hashlib
import json
import math
import re
import stat

from . import puck_on_policy as policy


_MAX_BYTES = 4 * 1024**2
_MAX_NODES = 65536
_MAX_DEPTH = 32
_MAX_IDENTITIES = 4096
_KINDS = {
    'on_policy_inventory', 'on_policy_reservation', 'on_policy_scene_manifest',
    'on_policy_collection_projection', 'on_policy_publication_commit',
    'on_policy_publication_admission',
}
_HASH_FIELDS = ('canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
_PROJECTION_FIELDS = {'version', 'kind', 'scene_ids', 'scenes'}
_TARGET_KINDS = {'reservation.json': 'on_policy_reservation',
                 'scene-manifest.json': 'on_policy_scene_manifest'}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate registry JSON key')
        result[key] = value
    return result


def _nonfinite(text):
    raise ValueError('Nonfinite registry JSON number')


def _bounded_tree(value):
    count = 0

    def visit(item, depth):
        nonlocal count
        count += 1
        if count > _MAX_NODES or depth > _MAX_DEPTH:
            raise ValueError('Registry JSON structure bound exceeded')
        if type(item) is dict:
            for child in item.values():
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        elif type(item) is float and not math.isfinite(item):
            raise ValueError('Nonfinite registry JSON number')

    visit(value, 0)


def _exact(value, fields, kind):
    if (type(value) is not dict or set(value) != fields or
            type(value['version']) is not int or value['version'] != 1 or
            value['kind'] != kind):
        raise ValueError('Exact registry document schema required')


def _sha(value, label):
    return policy._digest(value, label)


def _lineage(value):
    if _sha(value, 'registry lineage') != policy.PROTOCOL_SHA256:
        raise ValueError('Registry lineage differs from frozen protocol')


def _reference(kind, sha, pointer, relation, path=None):
    return {'kind': kind, 'sha256': sha, 'path': path,
            'path_base': 'content_digest' if path is None else 'document_directory',
            'pointer': pointer, 'relation': relation}


def _reject_metadata_declarations(value):
    # Metadata is diagnostic only; geometry declarations belong in typed scenes.
    # Numeric counters are allowed, but reserved declaration keys and aliases
    # cannot silently disappear from collision accounting.
    sensitive = {'scene', 'scenes', 'seed', 'seeds', 'split', 'splits',
        'layout', 'layouts', 'geometry', 'geometries', 'world', 'worlds'}
    coordinates = {'rover_pose', 'puck_xy', 'puck_xyz', 'goal_xy',
        'initial_puck_xy', 'previous_puck_xy', 'previous_rover_xy',
        'puck_velocity_xy', 'initial_qvel'}
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, child in item.items():
                normalized = re.sub(r'([a-z])([A-Z])', r'\1_\2', key).lower()
                tokens = [token for token in re.split(r'[^a-z0-9]+', normalized) if token]
                field = '_'.join(tokens)
                if set(tokens) & sensitive or field in coordinates or field in _HASH_FIELDS:
                    raise ValueError('Registry metadata contains an unsupported scene/geometry declaration')
                stack.append(child)
        elif type(item) is list:
            stack.extend(item)


def _inventory_scenes(inventory, prefix):
    scenes = []
    for record_index, record in enumerate(inventory['records']):
        _reject_metadata_declarations(record['metadata'])
        for scene_index, declaration in enumerate(record['scenes']):
            scenes.append({**declaration,
                'pointer': f'{prefix}/records/{record_index}/scenes/{scene_index}',
                'split': None, 'role': record['role'],
                'lineage_sha256': record['lineage_sha256'], 'layout_bound': False})
            if len(scenes) > _MAX_IDENTITIES:
                raise ValueError('Registry scene/reference bound exceeded')
    return scenes


def _reservation(raw, value):
    # The legacy pure validator checks exact inventory digests and occupied sets.
    # Explicit JSON list and scalar types close equality aliases in its comparisons.
    policy._ids(value.get('scene_ids'), 'reservation roster', exact_length=8)
    for field in ('inventory_before_sha256', 'inventory_after_sha256'):
        _sha(value.get(field), field)
    policy._ids(value.get('occupied_scene_ids'), 'occupied scene IDs')
    for field in _HASH_FIELDS:
        values = value.get('occupied_' + field)
        if type(values) is not list:
            raise ValueError('Reservation occupied hashes must be lists')
        for digest in values:
            _sha(digest, field)
    return policy._read_reservation(raw)


def _layout_scenes(value, *, collection):
    fields = _PROJECTION_FIELDS if collection else policy._SCENE_MANIFEST_FIELDS
    schema = ('puck-on-policy-collection-projection-v1' if collection else
              'puck-on-policy-scene-manifest-v1')
    _exact(value, fields, schema)
    lineage = None
    references = []
    if not collection:
        _lineage(value['lineage_sha256'])
        lineage = value['lineage_sha256']
        reservation_sha = _sha(value['reservation_sha256'], 'registry reservation')
        references.append(_reference('on_policy_reservation', reservation_sha,
                                     '/reservation_sha256', 'reservation'))
    roster = policy.RESERVED_SCENE_IDS[:4] if collection else policy.RESERVED_SCENE_IDS
    if (type(value['scene_ids']) is not list or
            policy._ids(value['scene_ids'], 'registry roster', exact_length=len(roster)) != roster or
            type(value['scenes']) is not list or len(value['scenes']) != len(roster)):
        raise ValueError('Registry ordered scene roster differs')
    scenes = []
    seen = {field: set() for field in _HASH_FIELDS}
    for slot, (scene_id, entry) in enumerate(zip(roster, value['scenes'])):
        split = policy.COLLECTION_SPLIT if slot < 4 else policy.DEVELOPMENT_SPLIT
        identities = policy._validate_scene_entry(entry, scene_id, slot, split)
        if any(digest in seen[field] for field, digest in identities.items()):
            raise ValueError('Registry cross-entry identity collision')
        for field, digest in identities.items():
            seen[field].add(digest)
        scenes.append({'scene_id': scene_id, **identities, 'pointer': f'/scenes/{slot}',
                       'split': split, 'role': 'collection' if collection else 'minted',
                       'lineage_sha256': lineage, 'layout_bound': True})
    return scenes, references


def _size(value):
    if type(value) is not int or not 0 < value <= _MAX_BYTES:
        raise ValueError('Positive bounded registry publication byte length required')
    return value


def _identity(value, size):
    # Same seven stat fields and regular/single-link semantics as _admission_receipt.
    # These supplied integers are not evidence about the present filesystem.
    if (type(value) is not list or len(value) != 7 or
            any(type(item) is not int for item in value) or
            not stat.S_ISREG(value[2]) or value[3] != 1 or value[4] != size):
        raise ValueError('Exact historical publication identity required')


def _publication_references(value, *, admission):
    fields = policy._ADMISSION_RECEIPT_FIELDS if admission else policy._COMMIT_RECEIPT_FIELDS
    schema = ('puck-on-policy-publication-admission-v1' if admission else
              'puck-on-policy-publication-commit-v1')
    _exact(value, fields, schema)
    target = value['target']
    if type(target) is not str or target not in _TARGET_KINDS:
        raise ValueError('Exact registry publication target required')
    _lineage(value['protocol_sha256'])
    manifest_sha = _sha(value['manifest_sha256'], 'publication target')
    reservation_sha = _sha(value['reservation_sha256'], 'publication reservation')
    _size(value['manifest_bytes'])
    if target == 'reservation.json' and reservation_sha != manifest_sha:
        raise ValueError('Reservation publication digest differs')
    references = [_reference(_TARGET_KINDS[target], manifest_sha, '/target',
                             'publication_target', target)]
    if admission:
        receipt = target + '.commit.json'
        if value['receipt'] != receipt:
            raise ValueError('Exact registry publication commit name required')
        receipt_sha = _sha(value['receipt_sha256'], 'publication commit')
        _size(value['receipt_bytes'])
        _identity(value['manifest_identity'], value['manifest_bytes'])
        _identity(value['receipt_identity'], value['receipt_bytes'])
        references.append(_reference('on_policy_publication_commit', receipt_sha,
                                     '/receipt', 'commit_receipt', receipt))
    if target == 'scene-manifest.json':
        references.append(_reference('on_policy_reservation', reservation_sha,
                                     '/reservation_sha256', 'reservation'))
    return references


def parse_puck_registry_document(raw: bytes, *, kind: str):
    """Validate one explicit registry schema and return byte-only identities.

    Dependencies are declared pins only. Authenticating their closure and any
    current filesystem custody belongs to a separate caller-controlled resolver.
    """
    if type(kind) is not str or kind not in _KINDS:
        raise ValueError('Explicit supported registry document kind required')
    if type(raw) is not bytes or not 0 < len(raw) <= _MAX_BYTES:
        raise ValueError('Bounded canonical registry bytes required')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
        _bounded_tree(value)
        if policy._canonical_bytes(value, 'registry document') != raw or type(value) is not dict:
            raise ValueError('Canonical registry object bytes required')
        scenes, references = [], []
        if kind == 'on_policy_inventory':
            policy._validate_inventory(value, policy.PROTOCOL_SHA256)
            scenes = _inventory_scenes(value, '')
        elif kind == 'on_policy_reservation':
            reservation = _reservation(raw, value)
            scenes = _inventory_scenes(reservation['inventory'], '/inventory')
        elif kind in ('on_policy_scene_manifest', 'on_policy_collection_projection'):
            scenes, references = _layout_scenes(value, collection=kind.endswith('projection'))
        else:
            references = _publication_references(value, admission=kind.endswith('admission'))
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError, KeyError, OverflowError) as error:
        raise ValueError('Strict registry document required') from error
    if len(scenes) + len(references) > _MAX_IDENTITIES:
        raise ValueError('Registry scene/reference bound exceeded')
    return {'kind': 'puck-registry-scene-identities-v1', 'document_kind': kind,
            'document_sha256': hashlib.sha256(raw).hexdigest(), 'document_bytes': len(raw),
            'scenes': scenes, 'references': references, 'inventory_complete': False,
            'source_closure_authenticated': False, 'executable': False,
            'native_authorized': False, 'collection_authorized': False,
            'qualification_claims': []}
