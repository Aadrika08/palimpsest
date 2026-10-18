"""Check supplied collection descriptions without granting execution authority."""
import copy
from pathlib import PurePosixPath

from . import artifacts, puck_on_policy as p

MiB = 1024**2
MODEL_INDEX_SHA256 = 'd8a2daf24943e5e8a2abf5062458910a1034dd003f8aa5153c32f0f83567502f'
RUNTIME = {'python':'3.11.15','numpy':'2.2.5','torch':'2.9.0','mujoco':'3.3.6',
           'backend':'egl','device':'cpu','training_and_inference_threads':1}
LIMITS = {'owner_seconds':180,'owner_bytes':160*MiB,'snapshot_bytes':8*MiB,
          'stdout_bytes':MiB,'stderr_bytes':MiB,'metadata_bytes':MiB,
          'recording_bytes':149*MiB,'intervals':600,'active_children':1,
          'stage_bytes':3*1024**3,'rss_bytes':1024**3,'free_bytes':1024**3,
          'retained_bytes':16*1024**3,'child_seconds':2160,'parent_seconds':50,
          'return_seconds':50,'hard_margin_seconds':10,'internal_seconds':2210,
          'normal_seconds':2260,'hard_seconds':2270}
_FREEZE = {'version','kind','protocol_sha256','stage','projection_sha256',
           'model_index_sha256','sources','runtime','upstream_sha256','limits',
           'attempt','output_root','owners','qualification_claims','executable'}
_ENVELOPE = {'version','kind','protocol_sha256','execution_freeze_sha256',
             'ordinal','owner','attempt','projection_sha256','model_index_sha256',
             'sources_sha256','runtime_sha256','qualification_claims','executable'}
_INVOCATION = {'owner_id','scene_id','model_seed','argv','environment','cwd','output'}
_REQUIRED_SOURCES = {'src/palimpsest/__init__.py','src/palimpsest/puck_on_policy.py',
                     'src/palimpsest/puck_collection_admission.py'}


def _fields(value, keys, label):
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f'{label}: exact fields required')


def _equal(value, expected, label):
    if p._canonical_bytes(value,label) != p._canonical_bytes(expected,label):
        raise ValueError(f'{label}: frozen identity differs')


def _read(raw, maximum, label, *, canonical=True):
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise ValueError(f'{label}: bounded bytes required')
    value = artifacts._json(raw)
    if canonical and p._canonical_bytes(value,label) != raw:
        raise ValueError(f'{label}: canonical bytes required')
    return value


def _path(value, label, *, absolute):
    if type(value) is not str or not value or len(value)>4096 or '\x00' in value:
        raise ValueError(f'{label}: bounded path required')
    path = PurePosixPath(value)
    if path.is_absolute()!=absolute or '..' in path.parts or path.as_posix()!=value:
        raise ValueError(f'{label}: canonical path required')
    return value


def admit_collection_envelope(envelope_raw, *, execution_freeze_raw,
        expected_execution_freeze_sha256, collection_projection_raw,
        original_model_index_raw, source_before, source_after, runtime_observation):
    """Return a copied source-only owner description with executable=False.

    The expected hash is externally supplied. Closure completeness and live
    runtime measurement remain separate prerequisites, not facts proved here.
    """
    p._digest(expected_execution_freeze_sha256,'Expected description')
    freeze = _read(execution_freeze_raw,MiB,'Execution description')
    if p._sha256(execution_freeze_raw)!=expected_execution_freeze_sha256:
        raise ValueError('Execution description differs from expected hash')
    _fields(freeze,_FREEZE,'Execution description')
    for key,value in {'version':1,'kind':'puck-collection-source-freeze-v1',
            'protocol_sha256':p.PROTOCOL_SHA256,'stage':'collection','attempt':1,
            'qualification_claims':[],'executable':False}.items():
        _equal(freeze[key],value,key)
    _equal(freeze['limits'],LIMITS,'Allocation')
    _equal(freeze['runtime'],RUNTIME,'Runtime')
    p._digest(freeze['upstream_sha256'],'Upstream digest')
    _equal(runtime_observation,{**RUNTIME,'upstream_sha256':freeze['upstream_sha256']},
           'Runtime observation')
    sources = freeze['sources']
    if type(sources) is not dict or not _REQUIRED_SOURCES<=set(sources) or len(sources)>1024:
        raise ValueError('Source closure lacks required paths or exceeds bound')
    for path,digest in sources.items():
        _path(path,'Source',absolute=False)
        p._digest(digest,'Source digest')
    _equal(source_before,sources,'Before sources')
    _equal(source_after,sources,'After sources')
    output_root = _path(freeze['output_root'],'Output root',absolute=True)

    projection = _read(collection_projection_raw,64*1024,'Collection projection')
    _fields(projection,{'version','kind','scene_ids','scenes'},'Collection projection')
    _equal({k:projection[k] for k in ('version','kind','scene_ids')},
           {'version':1,'kind':'puck-on-policy-collection-projection-v1',
            'scene_ids':[6110,6111,6112,6113]},'Projection identity')
    scenes = projection['scenes']
    if type(scenes) is not list or len(scenes)!=4:
        raise ValueError('Exactly four collection scenes required')
    for slot,scene in enumerate(scenes):
        p._validate_scene_entry(scene,6110+slot,slot,p.COLLECTION_SPLIT)
    _equal(freeze['projection_sha256'],p._sha256(collection_projection_raw),'Projection hash')
    model_index = _read(original_model_index_raw,64*1024,'Original index',canonical=False)
    if p._sha256(original_model_index_raw)!=MODEL_INDEX_SHA256:
        raise ValueError('Original immutable model index differs')
    _equal(freeze['model_index_sha256'],MODEL_INDEX_SHA256,'Model index hash')

    owners = freeze['owners']
    if type(owners) is not list or len(owners)!=12:
        raise ValueError('Exactly twelve ordered owner invocations required')
    for ordinal,owner in enumerate(owners):
        _fields(owner,_INVOCATION,'Owner invocation')
        scene,seed = 6110+ordinal//3,21+ordinal%3
        owner_id = f'collection-{scene}-seed-{seed}'
        _equal({k:owner[k] for k in ('owner_id','scene_id','model_seed','output')},
               {'owner_id':owner_id,'scene_id':scene,'model_seed':seed,
                'output':f'{output_root}/{owner_id}'},'Owner roster/namespace')
        _path(owner['cwd'],'Working directory',absolute=True)
        _path(owner['output'],'Owner output',absolute=True)
        argv,environment = owner['argv'],owner['environment']
        if (type(argv) is not list or not 1<=len(argv)<=128 or
                any(type(arg) is not str or not arg or '\x00' in arg or len(arg)>4096 for arg in argv)
                or type(environment) is not dict or len(environment)>128 or
                any(type(k) is not str or not k or type(v) is not str or
                    '\x00' in k+v or len(k)+len(v)>4096 for k,v in environment.items())):
            raise ValueError('Bounded argv/environment required')

    envelope = _read(envelope_raw,64*1024,'Owner envelope')
    _fields(envelope,_ENVELOPE,'Owner envelope')
    ordinal = envelope['ordinal']
    if type(ordinal) is not int or not 0<=ordinal<12:
        raise ValueError('Exact owner ordinal required')
    expected = {'version':1,'kind':'puck-collection-source-envelope-v1',
        'protocol_sha256':p.PROTOCOL_SHA256,'execution_freeze_sha256':expected_execution_freeze_sha256,
        'ordinal':ordinal,'owner':owners[ordinal],'attempt':1,
        'projection_sha256':p._sha256(collection_projection_raw),'model_index_sha256':MODEL_INDEX_SHA256,
        'sources_sha256':p._sha256(p._canonical_bytes(sources,'Sources')),
        'runtime_sha256':p._sha256(p._canonical_bytes(RUNTIME,'Runtime')),
        'qualification_claims':[],'executable':False}
    _equal(envelope,expected,'Owner envelope')
    return copy.deepcopy({'puck_on_policy':expected,'owner':owners[ordinal],
        'scene':scenes[ordinal//3],'model':model_index['models'][ordinal%3],
        'limits':LIMITS,'executable':False,'qualification_claims':[]})
