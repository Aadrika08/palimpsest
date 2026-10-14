"""Pure scene inventories for standalone puck results and batch reports.

These historical receipts do not authenticate their referenced files, run native
code, or establish qualification. Partial failed publications remain readable.
"""
from posixpath import dirname

from .puck_scene_retained import (
    _Inventory, _ROW_FIELDS, _SPLITS, _CATALOG_PATH, _decode, _hash,
    _integer, _list, _object, _path, _pointer,
)

_KINDS = frozenset(('owner_result', 'construction_result', 'mechanics_report',
                    'construction_report', 'development_report'))
_FINGERPRINT_FIELDS = frozenset(('native_identity', 'full_model_sha256', 'profile',
    'integration', 'environment', 'world', 'contact', 'task', 'sensors8',
    'inputs9', 'own_cursor', 'rng'))
_MODEL_HASHES = frozenset(('training_report_sha256', 'checkpoint_sha256',
    'protocol_sha256', 'learning_protocol_sha256', 'training_objective_sha256',
    'supervisor_source_sha256'))


class _Reports(_Inventory):
    def catalog_pin(self, value, base, inherited=None, *, missing=True):
        if 'pushing_protocol_sha256' in value:
            pin = _hash(value['pushing_protocol_sha256'], base + '/pushing_protocol_sha256')
            if inherited is not None and pin != inherited:
                raise ValueError('Conflicting pushing protocol pins at ' + base)
            return pin
        if missing and inherited is None:
            self.result['missing_pins'].append(base + '/pushing_protocol_sha256')
        return inherited

    def source_maps(self, value, base, catalog):
        for name in ('sources', 'source_hashes'):
            if name in value:
                self.hash_map(value[name], _pointer(base, name))
                pins = {pin for path, pin in value[name].items() if _CATALOG_PATH.fullmatch(path)}
                if pins and catalog is not None and catalog not in pins:
                    raise ValueError('Catalog pin absent from source receipts at ' + base)

    def model(self, value, base, expected=None):
        _object(value, base)
        seed = _integer(value.get('training_seed'), base + '/training_seed')
        self.allowed.add(base + '/training_seed')
        if expected is not None and seed != expected:
            raise ValueError('Conflicting model seed aliases at ' + base)
        for name in _MODEL_HASHES & value.keys():
            _hash(value[name], _pointer(base, name))
        return seed

    def student(self, value, base, row, inherited):
        _object(value, base)
        catalog = self.catalog_pin(value, base, inherited, missing=False)
        self.model(value.get('model_identity'), base + '/model_identity', row.get('model_seed'))
        return catalog

    def document_row(self, row, base, catalog, *, mechanics=False):
        previous = self.catalog
        self.catalog = catalog
        try:
            return self.row(row, base, mechanics=mechanics)
        finally:
            self.catalog = previous

    def file_ref(self, path, pin, base, kind, scene=None, *, pin_pointer=None):
        path = _path(path, base + '/path')
        pin = _hash(pin, pin_pointer or base + '/sha256', nullable=True)
        if pin is None:
            self.result['missing_pins'].append(pin_pointer or base + '/sha256')
        self.result['references'].append({'kind': kind, 'path': path, 'sha256': pin,
            'scene_id': scene[0] if scene else None, 'split': scene[1] if scene else None,
            'pointer': base, 'path_base': 'recorded_cwd'})
        self.limit()

    def fingerprint(self, value, base):
        _object(value, base)
        if set(value) != {'sha256', 'fields'}:
            raise ValueError('Unsupported scientific fingerprint at ' + base)
        _hash(value['sha256'], base + '/sha256')
        fields = _object(value['fields'], base + '/fields')
        if set(fields) != _FINGERPRINT_FIELDS:
            raise ValueError('Unsupported scientific fingerprint fields at ' + base)
        self.hash_map(fields, base + '/fields')

    def initial_match(self, value, base, row, output, scene):
        _object(value, base)
        if not set(value) <= {'status', 'reference', 'fingerprint', 'expected_fingerprint'}:
            raise ValueError('Unsupported initial match receipt at ' + base)
        for name in ('fingerprint', 'expected_fingerprint'):
            if name in value:
                self.fingerprint(value[name], _pointer(base, name))
        reference = value.get('reference')
        if reference is None:
            return
        reference_base = base + '/reference'
        _object(reference, reference_base)
        if set(reference) != {'owner_id', 'result_sha256', 'snapshot_sha256'}:
            raise ValueError('Unsupported baseline receipt at ' + reference_base)
        if (row.get('model_seed') == 21 or
                reference['owner_id'] != f"student-dev-{row['seed']}-seed21"):
            raise ValueError('Conflicting same-scene baseline at ' + reference_base)
        _hash(reference['result_sha256'], reference_base + '/result_sha256', nullable=True)
        _hash(reference['snapshot_sha256'], reference_base + '/snapshot_sha256')
        if output is None:
            self.result['missing_pins'].append(reference_base + '/path')
            if reference['result_sha256'] is None:
                self.result['missing_pins'].append(reference_base + '/result_sha256')
            return
        parent = dirname(output)
        path = (parent + '/' if parent else '') + reference['owner_id'] + '/result.json'
        self.file_ref(path, reference['result_sha256'], reference_base, 'owner_result', scene,
                      pin_pointer=reference_base + '/result_sha256')
        self.result['references'][-1].update(expected_owner_id=reference['owner_id'],
            expected_snapshot_sha256=reference['snapshot_sha256'])

    def owner_result(self, value, base='', *, expected=None, output=None, catalog=None):
        _object(value, base)
        row = _object(value.get('row'), base + '/row')
        if expected is not None and row != expected:
            raise ValueError('Conflicting owner/result row at ' + base)
        catalog = self.catalog_pin(value, base, catalog, missing=False)
        if 'student_identity' in value:
            catalog = self.student(value['student_identity'], base + '/student_identity', row, catalog)
        scene = self.document_row(row, base + '/row', catalog, mechanics='split' not in row)
        self.receipts(value, base)
        if 'source_hashes' in value:
            self.source_maps({'source_hashes': value['source_hashes']}, base, catalog)
        if 'contact_ownership' in value:
            self.ownership(value['contact_ownership'], base + '/contact_ownership')
        if 'initial_match' in value:
            self.initial_match(value['initial_match'], base + '/initial_match', row, output, scene)

    def binary_receipt(self, value, base):
        _object(value, base)
        if set(value) != {'sha256', 'bytes'}:
            raise ValueError('Unsupported binary receipt at ' + base)
        _hash(value['sha256'], base + '/sha256')
        if type(value['bytes']) is not int or value['bytes'] < 0:
            raise ValueError('Invalid binary size at ' + base)

    def construction_result(self, value, base=''):
        _object(value, base)
        if 'task_state' in value:
            self.state(value['task_state'], base + '/task_state')
        for name in ('full_native_model', 'full_native_data'):
            if name in value:
                self.binary_receipt(value[name], _pointer(base, name))
        if 'cameras' in value:
            for name, receipt in _object(value['cameras'], base + '/cameras').items():
                self.binary_receipt(receipt, _pointer(base + '/cameras', name))

    def protocol_metadata(self, value, base, *, construction=False):
        _object(value, base)
        # This is an environment RNG setting, not an authored layout declaration.
        if 'environment_kwargs' in value:
            kwargs = _object(value['environment_kwargs'], base + '/environment_kwargs')
            if 'seed' in kwargs:
                _integer(kwargs['seed'], base + '/environment_kwargs/seed')
                self.allowed.add(base + '/environment_kwargs/seed')
        if construction:
            seed = _integer(value.get('layout_seed'), base + '/layout_seed')
            split = value.get('layout_split')
            if type(split) is not str or split not in _SPLITS:
                raise ValueError('Invalid construction layout split at ' + base)
            self.allowed.update((base + '/layout_seed', base + '/layout_split'))
            self.result['mentions'].append({'scene_id': seed, 'split': split,
                'pointer': base + '/layout_seed', 'catalog_sha256': self.catalog})
            self.result['held_out_mentions'] |= split == 'held_out'
            self.limit()

    def report(self, kind):
        document = self.document
        if 'schema' in document:
            raise ValueError('Historical puck reports have no schema discriminator')
        self.catalog = self.catalog_pin(document, '', missing=False)
        if kind == 'mechanics_report':
            protocol = _object(document.get('protocol'), '/protocol')
            self.catalog = self.catalog_pin(protocol, '/protocol', self.catalog)
            self.protocol_metadata(protocol, '/protocol')
        elif kind == 'construction_report':
            self.protocol_metadata(document.get('protocol'), '/protocol', construction=True)
        self.source_maps(document, '', self.catalog)
        if 'models' in document:
            for key, model in _object(document['models'], '/models').items():
                if not key.isascii() or not key.isdecimal() or str(int(key)) != key:
                    raise ValueError('Canonical model seed key required')
                self.model(model, _pointer('/models', key), _integer(int(key), '/models/' + key))
        if 'admission' in document:
            admission = _object(document['admission'], '/admission')
            if 'goals_each_model' in admission:
                counts = _object(admission['goals_each_model'], '/admission/goals_each_model')
                for key, count in counts.items():
                    if not key.isascii() or not key.isdecimal() or str(int(key)) != key:
                        raise ValueError('Canonical model seed key required')
                    _integer(int(key), '/admission/goals_each_model/' + key)
                    _integer(count, '/admission/goals_each_model/' + key)
        for index, owner in enumerate(_list(document.get('owners'), '/owners')):
            base = '/owners/' + str(index)
            _object(owner, base)
            construction = kind == 'construction_report'
            declared = {key: child for key, child in owner.items() if key in _ROW_FIELDS}
            scene = None if construction else self.document_row(
                declared, base, self.catalog, mechanics=kind == 'mechanics_report')
            output = None
            if 'output' in owner:
                output = _path(owner['output'], base + '/output')
                self.file_ref(output + '/result.json', owner.get('result_sha256'), base,
                    'construction_result' if construction else 'owner_result', scene,
                    pin_pointer=base + '/result_sha256')
                if 'manifest_sha256' in owner:
                    self.file_ref(output + '/recording/manifest.json', owner['manifest_sha256'],
                        base, 'recording_manifest', scene, pin_pointer=base + '/manifest_sha256')
            else:
                for pin_name in ('result_sha256', 'manifest_sha256'):
                    if pin_name in owner:
                        pin = _hash(owner[pin_name], _pointer(base, pin_name), nullable=True)
                        if base + '/output' not in self.result['missing_pins']:
                            self.result['missing_pins'].append(base + '/output')
                        if pin is None:
                            self.result['missing_pins'].append(_pointer(base, pin_name))
            if 'result' in owner:
                if construction:
                    self.construction_result(owner['result'], base + '/result')
                else:
                    self.owner_result(owner['result'], base + '/result', expected=declared,
                                      output=output, catalog=self.catalog)


def parse_puck_report_document(raw: bytes, *, kind: str):
    """Inventory explicit report kinds without target reads or cwd inference."""
    if kind not in _KINDS:
        raise ValueError('Unsupported puck report document kind')
    inventory = _Reports(_decode(raw), kind, raw)
    if kind == 'owner_result':
        inventory.owner_result(inventory.document)
    elif kind == 'construction_result':
        inventory.construction_result(inventory.document)
    else:
        inventory.report(kind)
    inventory.reject_untyped()
    return inventory.result
