"""Pure training-result, prepared-wrapper and model-index scene dependencies.

Model seeds and binary receipts are declarations, not scene layouts or authority.
Only caller-supplied JSON bytes are parsed; no paths, checkpoints or models open.
"""
import hashlib
import json
from .puck_scene_retained import _Inventory, _decode, _object, _list, _integer, _hash, _path

_KINDS = {'training_report', 'prepared_training', 'model_index'}
_MAX_ITEMS = 4096


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def _model(value, pointer):
    return _integer(value, pointer)


def _reference(inv, *,kind,path,pin,pointer,seed,base='recorded_cwd',size=None):
    inv.reference({'path':path,'sha256':pin},pointer,kind)
    ref=inv.result['references'][-1]
    ref.update(path_base=base,expected_model_seed=seed)
    if size is not None:ref['size_bytes']=size


def _report(inv):
    doc=inv.document
    if doc.get('status') not in ('failed','running','completed') or type(doc.get('training_completed')) is not bool:
        raise ValueError('Typed training result status required')
    seed=_model(doc.get('training_seed'),'/training_seed');inv.allowed.add('/training_seed')
    protocol_pin=_hash(doc.get('protocol_sha256'),'/protocol_sha256')
    if 'training_objective_sha256' in doc:
        _hash(doc['training_objective_sha256'],'/training_objective_sha256')
    if doc.get('held_out_used') is not False:
        raise ValueError('Training held-out use must remain false')
    names=set();protocol_found=False
    for index,entry in enumerate(_list(doc.get('files'),'/files')):
        pointer='/files/'+str(index)
        if type(entry) is not dict or set(entry)!={'path','sha256','bytes'}:
            raise ValueError('Exact training file ledger entry required')
        name=entry['path']
        if name not in ('protocol.json','checkpoint.npz') or name in names:
            raise ValueError('Unknown or duplicate training ledger file')
        names.add(name);pin=_hash(entry['sha256'],pointer+'/sha256')
        cap=4*1024**2 if name=='protocol.json' else 1024**2
        size=entry['bytes']
        if type(size) is not int or not 0<size<=cap:
            raise ValueError('Bounded training file byte length required')
        if name=='protocol.json':
            if pin!=protocol_pin:raise ValueError('Training protocol ledger pin differs')
            _reference(inv,kind='training_protocol',path=name,pin=pin,pointer=pointer,
                seed=seed,base='document_directory',size=size)
            protocol_found=True
    if not protocol_found:inv.result['missing_pins'].append('/files/protocol.json')
    inv.result['model_seed']=seed


def _prepared(inv):
    doc=inv.document
    if (set(doc)!={'status','training_performed','protocol','protocol_sha256'}
            or doc['status']!='prepared' or doc['training_performed'] is not False):
        raise ValueError('Exact prepared training wrapper required')
    protocol=_object(doc['protocol'],'/protocol');payload=_canonical(protocol)
    if _hash(doc['protocol_sha256'],'/protocol_sha256')!=hashlib.sha256(payload).hexdigest():
        raise ValueError('Embedded training protocol digest differs')
    child=_Inventory(protocol,'training_protocol',payload)
    child.training();child.reject_untyped()
    # Prefix all genuine typed locations; don't whitelist an entire opaque object.
    inv.allowed.update('/protocol'+pointer for pointer in child.allowed)
    inv.hash_maps.update('/protocol'+pointer for pointer in child.hash_maps)
    for key in ('mentions','references'):
        inv.result[key]=[{**row,'pointer':'/protocol'+row['pointer']} for row in child.result[key]]
    inv.result['missing_pins']=['/protocol'+pointer for pointer in child.result['missing_pins']]
    inv.result['held_out_mentions']=child.result['held_out_mentions']
    inv.result['model_seed']=_model(protocol['training_seed'],'/protocol/training_seed')


def _index(inv):
    doc=inv.document;models=_list(doc.get('models'),'/models')
    if not 1<=len(models)<=_MAX_ITEMS//2:
        raise ValueError('Bounded nonempty model index required')
    seeds=set();directories=set()
    for index,model in enumerate(models):
        pointer='/models/'+str(index)
        if type(model) is not dict or set(model)!={'seed','directory','files'}:
            raise ValueError('Exact model index entry required')
        seed=_model(model['seed'],pointer+'/seed');inv.allowed.add(pointer+'/seed')
        directory=_path(model['directory'],pointer+'/directory')
        if directory.startswith('/') or seed in seeds or directory in directories:
            raise ValueError('Model index identity or directory is aliased')
        seeds.add(seed);directories.add(directory)
        files=_object(model['files'],pointer+'/files')
        if set(files)!={'protocol.json','report.json','checkpoint.npz'}:
            raise ValueError('Exact model bundle file pins required')
        inv.hash_map(files,pointer+'/files')
        for name,kind in (('protocol.json','training_protocol'),('report.json','training_report')):
            _reference(inv,kind=kind,path=directory+'/'+name,pin=files[name],
                pointer=pointer+'/files/'+name,seed=seed)


def parse_puck_training_document(raw: bytes, *,kind: str):
    if type(kind) is not str or kind not in _KINDS:
        raise ValueError('Explicit supported training metadata kind required')
    inv=_Inventory(_decode(raw),kind,raw)
    {'training_report':_report,'prepared_training':_prepared,'model_index':_index}[kind](inv)
    inv.limit();inv.reject_untyped()
    return inv.result
