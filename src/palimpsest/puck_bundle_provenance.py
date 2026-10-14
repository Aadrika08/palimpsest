"""Supplied original bundle bytes; historical provenance grants no execution."""
import copy
import math

from . import artifacts, puck_model
from .puck_collection_admission import MODEL_INDEX_SHA256

MiB = 1024**2
PRODUCER = '82e2bd97b37832c2a7f84f6eda6a3eca98e02362'
COLLECTION_SHA256 = '3cf5044ac12fa80ebfed9aa044d0e983a94fcddb4e177da779a4684b944b518b'
LEARNING_PATH = 'docs/plans/m6-puck-learning-v2.json'
TASK_PATH = 'docs/plans/m6-puck-pushing-protocol-v5.json'
HISTORICAL_SOURCES = {
    'scripts/train_puck.py':'9e6f9322ee1fafd5efdca6941bd74842676ed4f0221f8c8a2d4569074604f67b',
    'src/palimpsest/puck_model.py':'27f3446c71f59937f49fed4faddc614e5a792413b74328e81b361c72dd7f06d5',
    'src/palimpsest/puck_learning.py':'fe0350b1f7becf263ffbe19b8c906651a4f7655306dc60407927dcc20244f88d',
    'src/palimpsest/puck_profile.py':'585d41691d275313b276d49213249427ac645f7aa85fee544a05c37d2e652e2d',
    'src/palimpsest/artifacts.py':'7a5f4a1080abffe82f8296468c6d8ca3a2b975277b96925fdf75bb9ac1ed034a',
    'src/palimpsest/records.py':'c4be6f1699c1d8550a7f2db2979f7f9f18196ac986eef2aefe3ba665cae99ac3',
    'src/palimpsest/storage.py':'79664d876834ef20b459cc83963515effdaf75d0256fe5764a9cf8e18cd448c2',
    LEARNING_PATH:'bfdd047c1763af3d0b254c55df9137e179b65ce99e7eb870ca76f41332a83354',
    TASK_PATH:'77ce33fa593247715abe99ff2ba0eca399edbac44b29a580d4f92410b8013c30',
}
_BUNDLE_CAPS = {'report.json':4*MiB,'protocol.json':4*MiB,'checkpoint.npz':MiB}


def _bytes(raw, maximum, label):
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise ValueError(label + ': bounded immutable bytes required')
    return raw


def _object(raw, maximum, label):
    value = artifacts._json(_bytes(raw, maximum, label))
    if type(value) is not dict:
        raise ValueError(label + ': JSON object required')
    return value


def _equal(value, expected, label):
    if puck_model.canonical(value) != puck_model.canonical(expected):
        raise ValueError(label + ': historical identity differs')


def _bundle(bundle_payloads):
    if type(bundle_payloads) is not dict or set(bundle_payloads) != set(_BUNDLE_CAPS):
        raise ValueError('Exact three bundle payloads required')
    for name, cap in _BUNDLE_CAPS.items():
        _bytes(bundle_payloads[name], cap, name)


def _seed(seed):
    if type(seed) is not int or seed not in (21,22,23):
        raise ValueError('Exact original model seed required')


def _validate_lineage(*, seed, bundle_payloads, historical_source_payloads,
                      expected_source_hashes, expected_collection_sha256):
    """Generic lineage core, not an original-bundle or execution authority."""
    _seed(seed)
    _bundle(bundle_payloads)
    if (type(historical_source_payloads) is not dict or
            type(expected_source_hashes) is not dict or
            set(historical_source_payloads) != set(HISTORICAL_SOURCES) or
            set(expected_source_hashes) != set(HISTORICAL_SOURCES)):
        raise ValueError('Exact historical producer source closure required')
    for name, expected in expected_source_hashes.items():
        if puck_model.sha(_bytes(historical_source_payloads[name],MiB,name)) != expected:
            raise ValueError('Historical source bytes differ: ' + name)
    report = _object(bundle_payloads['report.json'],4*MiB,'Report')
    protocol = _object(bundle_payloads['protocol.json'],4*MiB,'Training protocol')
    for name, expected in {'status':'completed','training_completed':True,
            'training_seed':seed,'held_out_used':False,'qualification_claims':[],
            'finalization_errors':[],
            'protocol_sha256':puck_model.sha(bundle_payloads['protocol.json'])}.items():
        _equal(report.get(name),expected,'Report '+name)
    for name, expected in {'schema':'puck-training-v1','training_seed':seed,
            'held_out_used':False,'qualification_claims':[],
            'learning_protocol_sha256':expected_source_hashes[LEARNING_PATH],
            'source_hashes':expected_source_hashes}.items():
        _equal(protocol.get(name),expected,'Protocol '+name)
    entries = [{'path':name,'sha256':puck_model.sha(bundle_payloads[name]),
                'bytes':len(bundle_payloads[name])} for name in ('protocol.json','checkpoint.npz')]
    _equal(report.get('files'),entries,'Report ledger')
    history = report.get('history')
    if (type(history) is not list or len(history) != 30 or
            any(type(row) is not dict or type(row.get('epoch')) is not int or
                row['epoch'] != i or type(row.get('dev_loss')) not in (int,float) or
                not math.isfinite(row['dev_loss']) or row['dev_loss'] < 0
                for i,row in enumerate(history,1))):
        raise ValueError('Thirty finite ordered epoch rows required')
    _equal(report.get('selected_epoch'),min(history,key=lambda row:row['dev_loss'])['epoch'],
           'Earliest recorded-dev minimum')
    spec = _object(historical_source_payloads[LEARNING_PATH],MiB,'Historical learning')
    _equal(spec.get('task_protocol'),{'path':TASK_PATH,'sha256':expected_source_hashes[TASK_PATH]},
           'Historical task protocol')
    _equal(spec.get('teacher_source_sha256'),expected_source_hashes['src/palimpsest/puck_profile.py'],
           'Historical teacher source')
    task = _object(historical_source_payloads[TASK_PATH],MiB,'Historical task')
    if type(task.get('learning')) is not dict or type(spec.get('learning')) is not dict:
        raise ValueError('Historical learning definitions required')
    _equal(protocol.get('learning'),task['learning'] | spec['learning'],'Historical learning')
    if type(spec.get('action_arithmetic')) is not dict:
        raise ValueError('Historical action arithmetic required')
    _equal(protocol.get('action_arithmetic'),spec['action_arithmetic'],'Historical action arithmetic')
    collection = protocol.get('collection_report')
    if (type(collection) is not dict or set(collection) != {'path','sha256'} or
            type(collection['path']) is not str or not 0 < len(collection['path']) <= 4096 or
            '\x00' in collection['path']):
        raise ValueError('Historical collection lineage required')
    _equal(collection['sha256'],expected_collection_sha256,'Historical collection digest')
    arrays = puck_model.read_checkpoint(bundle_payloads['checkpoint.npz'])
    return arrays, {'training_seed':seed,
        'training_report_sha256':puck_model.sha(bundle_payloads['report.json']),
        'protocol_sha256':puck_model.sha(bundle_payloads['protocol.json']),
        'checkpoint_sha256':puck_model.sha(bundle_payloads['checkpoint.npz']),
        'learning_protocol_sha256':expected_source_hashes[LEARNING_PATH],
        'task_protocol_sha256':expected_source_hashes[TASK_PATH],
        'supervisor_source_sha256':expected_source_hashes['src/palimpsest/puck_learning.py'],
        'collection_report_sha256':expected_collection_sha256,
        'historical_source_hashes':copy.deepcopy(expected_source_hashes),
        'qualification_claims':[], 'executable':False}


def admit_original_bundle_bytes(*, seed, original_model_index_raw,
                                bundle_payloads, historical_source_payloads):
    """Pin original artifacts before decoding; open no paths and import no Torch."""
    _seed(seed)
    index_raw = _bytes(original_model_index_raw,64*1024,'Original index')
    if puck_model.sha(index_raw) != MODEL_INDEX_SHA256:
        raise ValueError('Immutable original model index differs')
    index = _object(index_raw,64*1024,'Original index')
    entry = index['models'][seed-21]
    _equal(entry['seed'],seed,'Original index seed')
    _equal(index['producer_commit'],PRODUCER,'Historical producer')
    _bundle(bundle_payloads)
    for name in _BUNDLE_CAPS:
        if puck_model.sha(bundle_payloads[name]) != entry['files'][name]:
            raise ValueError('Original model artifact pin differs: ' + name)
    arrays, identity = _validate_lineage(seed=seed,bundle_payloads=bundle_payloads,
        historical_source_payloads=historical_source_payloads,
        expected_source_hashes=HISTORICAL_SOURCES,
        expected_collection_sha256=COLLECTION_SHA256)
    identity.update(original_model_index_sha256=MODEL_INDEX_SHA256,producer_commit=PRODUCER)
    return arrays, identity
