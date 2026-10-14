"""Bounded, pure inventory of scene references in historical puck metadata.

This module consumes supplied bytes only. It neither resolves files nor interprets
recorded world coordinates as authored reset geometry or qualification evidence.
"""
import hashlib
import json
import math
import re

_MAX_BYTES = 4 * 1024**2
_MAX_NODES = 65536
_MAX_DEPTH = 32
_MAX_ITEMS = 4096
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_CATALOG_PATH = re.compile(r'docs/plans/m6-puck-pushing-protocol(?:-v[1-5])?\.json\Z')
_MANIFESTS = frozenset(('puck-mechanics-v2', 'puck-demonstration-v1',
    'puck-student-v1', 'puck-balanced-student-v1', 'puck-student-development-v1',
    'puck-balanced-student-development-v1'))
_SPLITS = frozenset(('train', 'recorded_dev', 'closed_loop_dev', 'mechanics', 'held_out'))
_ROW_FIELDS = frozenset(('id', 'case', 'kind', 'seed', 'split', 'model_seed',
                        'boundary', 'max_ticks', 'max_bytes'))
_WORLD = {'time_s': None, 'rover_pose': 3, 'puck_xyz': 3, 'puck_velocity_xy': 2, 'goal_xy': 2}
_STATE_COORDS = {'initial_puck_xy': 2, 'previous_puck_xy': 2, 'previous_rover_xy': 2, 'goal_xy': 2}
_STATE_FIELDS = frozenset(('version', 'protocol_sha256', 'episode_id', 'tick',
    *_STATE_COORDS, 'previous_distance', 'had_contact', 'dwell_ticks', 'stall_ticks', 'reason'))
_SENSITIVE = frozenset(('scene', 'scenes', 'scene_id', 'scene_ids', 'seed', 'seeds',
    'split', 'splits', 'layout', 'layouts', 'layout_id', 'geometry', 'geometries',
    'world', 'world_before', 'world_after', 'final_world', 'rover_pose', 'puck_xyz',
    'puck_xy', 'goal_xy', 'puck_velocity_xy', *_STATE_COORDS))


def _pointer(base, key):
    return base + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _object(value, pointer):
    if type(value) is not dict:
        raise ValueError('Object required at ' + pointer)
    return value


def _list(value, pointer):
    if type(value) is not list:
        raise ValueError('List required at ' + pointer)
    return value


def _integer(value, pointer):
    if type(value) is not int or not 0 <= value <= 2**31 - 1:
        raise ValueError('Scene/model integer out of range at ' + pointer)
    return value


def _hash(value, pointer, *, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError('Lowercase SHA256 required at ' + pointer)
    return value


def _path(value, pointer):
    if (type(value) is not str or not value or value == '/' or
            any(ord(c) < 32 or ord(c) == 127 for c in value) or
            '\\' in value or ':' in value):
        raise ValueError('Canonical POSIX file/directory path required at ' + pointer)
    parts = value[1:].split('/') if value.startswith('/') else value.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Noncanonical path at ' + pointer)
    return value


def _decode(raw):
    if type(raw) is not bytes or len(raw) > _MAX_BYTES:
        raise ValueError('Document must be bytes within 4 MiB')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON object key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('Nonfinite JSON constant')

    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Invalid retained JSON') from error
    _object(value, '')
    nodes = 0

    def walk(current, pointer, depth):
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_NODES or depth > _MAX_DEPTH:
            raise ValueError('Retained JSON node/depth limit exceeded')
        if type(current) is float and not math.isfinite(current):
            raise ValueError('Nonfinite JSON number at ' + pointer)
        if type(current) is dict:
            for key, child in current.items():
                walk(child, _pointer(pointer, key), depth + 1)
        elif type(current) is list:
            for index, child in enumerate(current):
                walk(child, _pointer(pointer, index), depth + 1)

    walk(value, '', 0)
    return value


class _Inventory:
    def __init__(self, document, kind, raw):
        self.document = document
        self.allowed = set()
        self.hash_maps = set()
        self.catalog = None
        self.result = {'kind': 'puck-retained-scene-references-v1', 'document_kind': kind,
            'document_sha256': hashlib.sha256(raw).hexdigest(), 'document_bytes': len(raw),
            'mentions': [], 'references': [], 'missing_pins': [], 'held_out_mentions': False,
            'inventory_complete': False, 'source_closure_authenticated': False,
            'executable': False, 'qualification_claims': []}

    def pin(self, container, name, base, *, required=False):
        pointer = _pointer(base, name)
        if name not in container:
            if required:
                raise ValueError('Missing pin at ' + pointer)
            self.result['missing_pins'].append(pointer)
            return None
        return _hash(container[name], pointer)

    def limit(self):
        if len(self.result['mentions']) + len(self.result['references']) > _MAX_ITEMS:
            raise ValueError('Retained mention/reference limit exceeded')

    def scene(self, value, base, *, mechanics=False):
        _object(value, base)
        scene = _integer(value.get('seed'), _pointer(base, 'seed'))
        split = value.get('split', 'mechanics' if mechanics else None)
        if type(split) is not str or split not in _SPLITS or (mechanics and split != 'mechanics'):
            raise ValueError('Invalid scene split at ' + _pointer(base, 'split'))
        self.allowed.update((_pointer(base, 'seed'), _pointer(base, 'split')))
        self.result['mentions'].append({'scene_id': scene, 'split': split,
            'pointer': _pointer(base, 'seed'), 'catalog_sha256': self.catalog})
        self.result['held_out_mentions'] |= split == 'held_out'
        self.limit()
        return scene, split

    def row(self, value, base, *, mechanics=False, expected=None):
        _object(value, base)
        if not set(value) <= _ROW_FIELDS:
            raise ValueError('Unsupported row fields at ' + base)
        scene = self.scene(value, base, mechanics=mechanics)
        if expected is not None and scene != expected:
            raise ValueError('Conflicting scene roster at ' + base)
        if 'model_seed' in value:
            _integer(value['model_seed'], base + '/model_seed')
            self.allowed.add(base + '/model_seed')
        return scene

    def reference(self, source, base, reference_kind, *, directory=False, scene=None):
        name = 'manifest_sha256' if directory else 'sha256'
        if name not in source:
            raise ValueError('Missing reference pin field at ' + _pointer(base, name))
        pin = _hash(source[name], _pointer(base, name), nullable=True)
        if pin is None:
            self.result['missing_pins'].append(_pointer(base, name))
        path = _path(source.get('path'), base + '/path')
        self.result['references'].append({'kind': reference_kind,
            'path': path + '/manifest.json' if directory else path, 'sha256': pin,
            'scene_id': scene[0] if scene else None, 'split': scene[1] if scene else None,
            'pointer': base})
        self.limit()

    def coordinates(self, value, base, fields, *, exact=False):
        _object(value, base)
        if exact and set(value) != set(fields):
            raise ValueError('Unsupported world receipt fields at ' + base)
        for name, size in fields.items():
            if name not in value:
                raise ValueError('Missing coordinate receipt at ' + _pointer(base, name))
            child = value[name]
            numbers = [child] if size is None else child
            if size is not None and (type(child) is not list or len(child) != size):
                raise ValueError('Invalid coordinate receipt at ' + base)
            try:
                finite = all(type(n) in (int, float) and math.isfinite(n) for n in numbers)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError('Invalid coordinate number at ' + base)
            self.allowed.add(_pointer(base, name))

    def world(self, value, base):
        self.allowed.add(base)
        self.coordinates(value, base, _WORLD, exact=True)

    def state(self, value, base):
        _object(value, base)
        if set(value) != _STATE_FIELDS:
            raise ValueError('Unsupported task state receipt at ' + base)
        self.coordinates(value, base, _STATE_COORDS)

    def snapshot(self, value, base):
        _object(value, base)
        if set(value) != {'file', 'sha256', 'bytes', 'tick', 'application_sha256', 'world', 'contact'}:
            raise ValueError('Unsupported snapshot receipt at ' + base)
        _path(value['file'], base + '/file')
        _hash(value['sha256'], base + '/sha256')
        _hash(value['application_sha256'], base + '/application_sha256')
        for name in ('bytes', 'tick'):
            if type(value[name]) is not int or value[name] < (1 if name == 'bytes' else 0):
                raise ValueError('Invalid snapshot size/tick at ' + base)
        self.world(value['world'], base + '/world')
        _object(value['contact'], base + '/contact')

    def receipts(self, value, base):
        if 'source_hashes' in value:
            self.hash_map(value['source_hashes'], base + '/source_hashes')
        for name in ('source', 'source_snapshot'):
            if value.get(name) is not None:
                self.snapshot(value[name], _pointer(base, name))
        if 'snapshots' in value:
            for name, receipt in _object(value['snapshots'], base + '/snapshots').items():
                if name not in ('initial', 'tick1', 'contact', 'dwell'):
                    raise ValueError('Unsupported snapshot boundary')
                self.snapshot(receipt, _pointer(base + '/snapshots', name))
        if 'final_state' in value:
            self.state(value['final_state'], base + '/final_state')
        if 'final_world' in value:
            self.world(value['final_world'], base + '/final_world')

    def ownership(self, value, base):
        _object(value, base)
        if 'geometries' in value:
            self.allowed.add(base + '/geometries')
            for item in _list(value['geometries'], base + '/geometries'):
                if type(item) is not dict or set(item) != {'geom_id', 'name', 'body_id', 'body_name', 'owner'}:
                    raise ValueError('Unsupported named geometry inventory')

    def hash_map(self, value, base):
        for name, pin in _object(value, base).items():
            _hash(pin, _pointer(base, name))
        self.hash_maps.add(base)

    def root_catalog_receipts(self):
        """Check hash presence without selecting an active historical revision.

        The real source inventory retains the original protocol alongside v5.
        Different historical hashes therefore remain provenance receipts; only
        the explicit top pin binds mentions, and attachment remains unproved.
        """
        pins = {pin for name, pin in self.document.get('source_hashes', {}).items()
                if _CATALOG_PATH.fullmatch(name)}
        if pins and self.catalog is not None and self.catalog not in pins:
            raise ValueError('Pushing protocol pin absent from known catalog source receipts')

    def reject_untyped(self):
        stack = [(self.document, '')]
        while stack:
            value, base = stack.pop()
            if type(value) is dict:
                for name, child in value.items():
                    pointer = _pointer(base, name)
                    lower = name.lower()
                    normalized = re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()
                    tokens = re.split(r'[^a-z0-9]+', normalized)
                    normalized_field = '_'.join(token for token in tokens if token)
                    declaration = bool(set(tokens) & {'scene', 'scenes', 'seed', 'seeds',
                        'split', 'splits', 'layout', 'layouts', 'geometry', 'geometries'})
                    # Hash-map file names are receipts, not declaration field names.
                    sensitive = base not in self.hash_maps and (
                        lower in _SENSITIVE or normalized_field in _SENSITIVE or declaration)
                    if sensitive and pointer not in self.allowed:
                        raise ValueError('Unsupported scene/geometry declaration at ' + pointer)
                    stack.append((child, pointer))
            elif type(value) is list:
                stack.extend((child, _pointer(base, index)) for index, child in enumerate(value))

    def manifest(self):
        document = self.document
        schema = document.get('schema')
        if type(schema) is not str or schema not in _MANIFESTS:
            raise ValueError('Unsupported puck recording manifest schema')
        self.catalog = self.pin(document, 'pushing_protocol_sha256', '')
        mechanics = schema == 'puck-mechanics-v2'
        scene = self.row(document.get('row'), '/row', mechanics=mechanics)
        if not mechanics or 'seed' in document:
            if self.scene(document, '', mechanics=mechanics) != scene:
                raise ValueError('Conflicting top-level manifest scene')
        elif 'split' in document:
            if type(document['split']) is not str or document['split'] != 'mechanics':
                raise ValueError('Conflicting explicit mechanics split')
            self.allowed.add('/split')
        model = document.get('model_identity')
        if model is not None:
            _object(model, '/model_identity')
            seed = _integer(model.get('training_seed'), '/model_identity/training_seed')
            self.allowed.add('/model_identity/training_seed')
            if 'model_seed' in document['row'] and seed != document['row']['model_seed']:
                raise ValueError('Conflicting model identity aliases')
        self.receipts(document, '')
        self.root_catalog_receipts()
        if 'contact_ownership' in document:
            self.ownership(document['contact_ownership'], '/contact_ownership')

    def teacher(self):
        document = self.document
        if 'schema' in document:
            raise ValueError('Teacher collection reports have no schema discriminator')
        self.catalog = self.pin(document, 'pushing_protocol_sha256', '', required=True)
        self.pin(document, 'learning_protocol_sha256', '', required=True)
        if 'source_hashes' in document:
            self.hash_map(document['source_hashes'], '/source_hashes')
        self.root_catalog_receipts()
        for name in ('teacher_source_sha256', 'supervisor_source_sha256'):
            if name in document:
                _hash(document[name], '/' + name)
        sources = _list(document.get('sources'), '/sources')
        owners = _list(document.get('owners'), '/owners')
        admission = _object(document.get('admission'), '/admission')
        rows = _list(admission.get('rows'), '/admission/rows')
        if len(owners) != len(sources) or len(rows) > len(sources):
            raise ValueError('Conflicting teacher roster lengths')
        scenes = []
        for index, source in enumerate(sources):
            base = '/sources/' + str(index)
            if type(source) is not dict or set(source) != {'seed', 'split', 'path', 'manifest_sha256'}:
                raise ValueError('Unsupported teacher source receipt at ' + base)
            scene = self.scene(source, base)
            scenes.append(scene)
            self.reference(source, base, 'recording_manifest', directory=True, scene=scene)
        for index, owner in enumerate(owners):
            base = '/owners/' + str(index)
            _object(owner, base)
            declared = {key: value for key, value in owner.items() if key in _ROW_FIELDS}
            self.row(declared, base, expected=scenes[index])
            if 'result' in owner:
                result = _object(owner['result'], base + '/result')
                self.row(result.get('row'), base + '/result/row', expected=scenes[index])
                self.receipts(result, base + '/result')
                if 'contact_ownership' in result:
                    self.ownership(result['contact_ownership'], base + '/result/contact_ownership')
        for index, item in enumerate(rows):
            base = '/admission/rows/' + str(index)
            if self.scene(item, base) != scenes[index]:
                raise ValueError('Conflicting admission roster at ' + base)

    def training(self):
        document = self.document
        if document.get('schema') not in ('puck-training-v1', 'puck-balanced-training-v1'):
            raise ValueError('Unsupported puck training protocol schema')
        if 'pushing_protocol_sha256' in document:
            _hash(document['pushing_protocol_sha256'], '/pushing_protocol_sha256')
        if 'source_hashes' in document:
            self.hash_map(document['source_hashes'], '/source_hashes')
        _integer(document.get('training_seed'), '/training_seed')
        self.allowed.add('/training_seed')
        report = _object(document.get('collection_report'), '/collection_report')
        if set(report) != {'path', 'sha256'}:
            raise ValueError('Unsupported collection report receipt')
        self.reference(report, '/collection_report', 'teacher_collection_report')
        for index, source in enumerate(_list(document.get('sources'), '/sources')):
            base = '/sources/' + str(index)
            if type(source) is not dict or set(source) != {'seed', 'split', 'ticks', 'manifest_sha256',
                    'source_hashes', 'feature_sha256', 'target_sha256', 'path'}:
                raise ValueError('Unsupported training source receipt at ' + base)
            scene = self.scene(source, base)
            if type(source['ticks']) is not int or not 1 <= source['ticks'] <= 600:
                raise ValueError('Invalid training tick receipt at ' + base)
            for name in ('feature_sha256', 'target_sha256'):
                _hash(source[name], _pointer(base, name))
            self.hash_map(source['source_hashes'], base + '/source_hashes')
            pin = _hash(source['manifest_sha256'], base + '/manifest_sha256', nullable=True)
            numeric_pin = source['source_hashes'].get('manifest.json')
            if pin is not None and numeric_pin is not None and numeric_pin != pin:
                raise ValueError('Conflicting training manifest receipt at ' + base)
            self.reference(source, base, 'recording_manifest', directory=True, scene=scene)


def parse_retained_puck_document(raw: bytes, *, kind: str):
    """Extract typed mentions and file references without reading their targets.

    ``kind`` is explicit; referenced hashes are receipts, never proof of closure.
    Missing nullable reference pins are retained and listed as missing pins.
    """
    if kind not in ('recording_manifest', 'teacher_collection_report', 'training_protocol'):
        raise ValueError('Unsupported retained document kind')
    inventory = _Inventory(_decode(raw), kind, raw)
    {'recording_manifest': inventory.manifest, 'teacher_collection_report': inventory.teacher,
     'training_protocol': inventory.training}[kind]()
    inventory.reject_untyped()
    return inventory.result
