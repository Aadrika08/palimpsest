"""Pure historical task-catalog identities, never inventory/execution admission.

Parsing whole public task JSON exposes its catalog coordinates. The real scanner
must separately admit that access or use a reviewed identity-only projection.
No files, runtime model, native state or retained evidence are opened here.
"""
import hashlib
import json
import math


_TASKS={f'm6-puck-pushing-plan-v{version}' for version in range(1,6)}
_LAYOUT={'seed','split','rover_pose','puck_xy','goal_xy','initial_qvel'}
_PHYSICS={'seed','id','action','check','rover_pose','puck_xy','goal_xy','ticks'}
_TEACHER_PHYSICS=(_PHYSICS-{'action'})|{'controller'}
_RESERVED={6110,6111,6112,6113,6120,6121,6122,6123}
_SPLITS={'train':range(6000,6016),'recorded_dev':range(6016,6020),
         'closed_loop_dev':range(6100,6104),'held_out':range(6200,6208)}
_SCENE_KEYS={'scene','scene_id','scene_ids','scene_order','scenes','layout_seed',
             'layout_split','layout','layouts','physics_cases'}
_ROW_KEYS={'seed','split','rover_pose','puck_xy','goal_xy','initial_qvel'}
_MAX_BYTES=4*1024**2


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate task catalog JSON key')
        value[key]=item
    return value


def _id(value):
    if type(value) is not int or not 0<=value<=2**31-1 or value in _RESERVED:
        raise ValueError('Exact nonreserved historical scene ID required')
    return value


def _vector(value,size,label):
    if type(value) is not list or len(value)!=size:
        raise ValueError('Exact historical geometry vector required: '+label)
    result=[]
    for number in value:
        if type(number) not in (int,float):
            raise ValueError('Finite canonical historical geometry required')
        try:converted=float(number)
        except OverflowError as error:
            raise ValueError('Historical geometry conversion overflow') from error
        if not math.isfinite(converted) or converted==0 and math.copysign(1,converted)<0:
            raise ValueError('Finite canonical historical geometry required')
        result.append(converted)
    return result


def _bounded_tree(value):
    count=0
    def visit(item,depth,path):
        nonlocal count
        count+=1
        if count>4096 or depth>32:raise ValueError('Task catalog structure bound exceeded')
        if type(item) is dict:
            for key,child in item.items():
                row_path=(len(path)==2 and path[0] in ('layouts','physics_cases')
                          and type(path[1]) is int)
                if (key in _SCENE_KEYS and not (not path and key in ('layouts','physics_cases'))
                        or key in _ROW_KEYS and not row_path):
                    raise ValueError('Unrecognized scene-bearing task catalog field: '+str(path+(key,)))
                visit(child,depth+1,path+(key,))
        elif type(item) is list:
            for index,child in enumerate(item):visit(child,depth+1,path+(index,))
        elif type(item) is float and not math.isfinite(item):
            raise ValueError('Nonfinite task catalog JSON')
    visit(value,0,())


def _scene(payload,pointer):
    scene_id=_id(payload['seed'])
    pose=_vector(payload['rover_pose'],3,'rover_pose')
    puck=_vector(payload['puck_xy'],2,'puck_xy')
    goal=_vector(payload['goal_xy'],2,'goal_xy')
    if max(map(abs,pose[:2]+puck+goal))>5 or abs(pose[2])>math.pi:
        raise ValueError('Historical geometry outside fixed arena')
    if payload['initial_qvel']!='all zeros':
        raise ValueError('Historical initial velocity contract differs')
    canonical={'version':1,'kind':'puck-on-policy-canonical-scene-v1',
               'rover_pose':pose,'puck_xy':puck,'goal_xy':goal}
    initial={**canonical,'kind':'puck-on-policy-scientific-initial-v1',
             'initial_qvel':'all zeros'}
    return {'scene_id':scene_id,'split':payload['split'],'pointer':pointer,
        'canonical_scene_sha256':_hash(canonical),
        'scientific_initial_sha256':_hash(initial),'payload_sha256':_hash(payload)}


def parse_task_catalog(raw):
    """Extract exact supported historical schemas, including catalog exposure.

    Caller-supplied bytes are not an authenticated complete inventory. Coordinate
    normalization agrees with the v3 geometry/scientific hash domains; payload
    hashes retain genuine old layout bytes, without fabricated v3 slots.
    """
    if type(raw) is not bytes or not 0<len(raw)<=_MAX_BYTES:
        raise ValueError('Bounded historical task catalog bytes required')
    try:
        value=json.loads(raw,object_pairs_hook=_pairs,
            parse_constant=lambda text:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError) as error:
        raise ValueError('Strict task catalog JSON required') from error
    if (type(value) is not dict or type(value.get('id')) is not str or value['id'] not in _TASKS
            or type(value.get('version')) is not int or value['version']!=1):
        raise ValueError('Exact supported historical task catalog identity required')
    _bounded_tree(value)
    for field in ('layouts','physics_cases'):
        if type(value.get(field)) is not list or not 1<=len(value[field])<=4096:
            raise ValueError('Complete bounded historical '+field+' roster required')
    scenes=[];seen=set()
    for index,row in enumerate(value['layouts']):
        if type(row) is not dict or set(row)!=_LAYOUT:
            raise ValueError('Exact historical layout fields required')
        seed=_id(row['seed']);split=row['split']
        if type(split) is not str or split not in _SPLITS or seed not in _SPLITS[split]:
            raise ValueError('Historical scene/split identity differs')
        scenes.append(_scene(row,'/layouts/'+str(index)))
    for index,row in enumerate(value['physics_cases']):
        if type(row) is not dict or set(row) not in (_PHYSICS,_TEACHER_PHYSICS):
            raise ValueError('Exact historical mechanics fields required')
        # This is the payload returned by the unchanged puck_profile.layout;
        # controller action/check/ticks are not authored scene/reset geometry.
        payload={key:row[key] for key in ('seed','rover_pose','puck_xy','goal_xy')}
        payload.update(split='mechanics',initial_qvel='all zeros')
        if (type(row['id']) is not str or not 0<len(row['id'])<=256
                or type(row['check']) is not str or not 0<len(row['check'])<=256
                or type(row['ticks']) is not int or not 1<=row['ticks']<=600):
            raise ValueError('Historical mechanics contract differs')
        if ('action' in row and max(map(abs,_vector(row['action'],2,'mechanics action')))>0.4
                or 'controller' in row and row['controller']!='puck-teacher'):
            raise ValueError('Historical mechanics controller differs')
        scenes.append(_scene(payload,'/physics_cases/'+str(index)))
    for scene in scenes:
        if scene['scene_id'] in seen:
            raise ValueError('Duplicate historical scene definition within one catalog')
        seen.add(scene['scene_id'])
    return {'kind':'puck-historical-task-catalog-identities-v1',
        'document_sha256':hashlib.sha256(raw).hexdigest(),'document_bytes':len(raw),
        'schema':value['id'],'scenes':scenes,
        'held_out_catalog_read':any(scene['split']=='held_out' for scene in scenes),
        'held_out_runtime_opened':False,'inventory_complete':False,
        'executable':False,'qualification_claims':[]}


# Source ceilings inside the prospective registry stage, never extra allocation.
_MAX_DOCUMENT_OCCURRENCES = _MAX_VARIANTS = 4096
_MAX_SCENE_OCCURRENCES = 65536
_MAX_OCCURRENCE_INPUT_BYTES = 32 * 1024 ** 2
_MAX_OCCURRENCE_METADATA_BYTES = 64 * 1024 ** 2
_DOCUMENT_FIELDS = {'repository', 'object_format', 'commit', 'root_tree',
                    'path', 'oid', 'mode', 'raw'}
_IDENTITY_FIELDS = ('canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')


def assemble_task_catalog_occurrences(documents, *, deadline):
    """Preserve task-catalog variants and occurrences without inventory admission.

    Blob framing binds supplied bytes to their OID. Commit/tree attachment,
    repository scope, fresh refs and filesystem custody are NOT proved by caller
    descriptors. Other scene-bearing schema families require separate dispatch.
    Compatibility below concerns old scene-row uniqueness only, never a complete
    inventory or permission to reserve or execute.
    """
    import time
    from pathlib import PurePosixPath
    import re

    now = time.monotonic()
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or deadline > now + 600:
        raise ValueError('Bounded finite catalog assembly deadline required')

    def clock():
        if time.monotonic() >= deadline:
            raise TimeoutError('Catalog assembly deadline exhausted')

    def path(value, *, absolute):
        if (type(value) is not str or not value or '\\' in value
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
                or value.startswith('//') or value != str(PurePosixPath(value))
                or value.startswith('/') != absolute
                or any(part in ('', '.', '..') for part in value.split('/')[1 if absolute else 0:])):
            raise ValueError('Canonical catalog occurrence path required')
        return value

    clock()
    if type(documents) is not list or not 1 <= len(documents) <= _MAX_DOCUMENT_OCCURRENCES:
        raise ValueError('Bounded nonempty catalog document occurrences required')
    grouped, locations, parsed_blobs = {}, set(), {}
    repository_formats, commit_trees = {}, {}
    input_bytes = metadata_bytes = occurrence_count = 0
    exposed = False
    for document in documents:
        clock()
        if type(document) is not dict or set(document) != _DOCUMENT_FIELDS:
            raise ValueError('Exact catalog document occurrence fields required')
        repository = path(document['repository'], absolute=True)
        doc_path = path(document['path'], absolute=False)
        if not doc_path.casefold().endswith('.json'):
            raise ValueError('Supported task catalog JSON document required')
        algorithm = document['object_format']
        if type(algorithm) is not str or algorithm not in ('sha1', 'sha256'):
            raise ValueError('Registered Git object format required')
        if repository_formats.setdefault(repository, algorithm) != algorithm:
            raise ValueError('Catalog repository object formats conflict')
        width = 40 if algorithm == 'sha1' else 64
        for field in ('commit', 'root_tree', 'oid'):
            if type(document[field]) is not str or re.fullmatch('[0-9a-f]{'+str(width)+'}', document[field]) is None:
                raise ValueError('Canonical catalog Git object identity required')
        if type(document['mode']) is not str or document['mode'] not in ('100644', '100755'):
            raise ValueError('Regular catalog Git document mode required')
        commit_key = repository, document['commit']
        if commit_trees.setdefault(commit_key, document['root_tree']) != document['root_tree']:
            raise ValueError('Catalog commit root-tree descriptors conflict')
        payload = document['raw']
        if type(payload) is not bytes or not 0 < len(payload) <= _MAX_BYTES:
            raise ValueError('Bounded task catalog bytes required')
        input_bytes += len(payload)
        if input_bytes > _MAX_OCCURRENCE_INPUT_BYTES:
            raise ValueError('Catalog aggregate input exceeds source ceiling')
        digest = hashlib.new(algorithm)
        digest.update(b'blob ' + str(len(payload)).encode() + b'\0')
        digest.update(payload)
        if digest.hexdigest() != document['oid']:
            raise ValueError('Catalog Git blob binding differs')
        location = (repository, document['commit'], doc_path)
        if location in locations:
            raise ValueError('Repeated or conflicting catalog document occurrence')
        locations.add(location)
        key = algorithm, document['oid']
        if key not in parsed_blobs:
            parsed_blobs[key] = parse_task_catalog(payload)
        parsed = parsed_blobs[key]
        exposed |= parsed['held_out_catalog_read']
        clock()
        for scene in parsed['scenes']:
            clock()
            identity = (scene['scene_id'], *(scene[field] for field in _IDENTITY_FIELDS))
            occurrence = {field: document[field] for field in _DOCUMENT_FIELDS - {'raw'}}
            occurrence.update(document_sha256=parsed['document_sha256'],
                              schema=parsed['schema'], pointer=scene['pointer'], split=scene['split'])
            metadata_bytes += len(_canonical(occurrence))
            occurrence_count += 1
            if (metadata_bytes > _MAX_OCCURRENCE_METADATA_BYTES
                    or occurrence_count > _MAX_SCENE_OCCURRENCES):
                raise ValueError('Catalog occurrence metadata exceeds source ceiling')
            if identity not in grouped:
                if len(grouped) >= _MAX_VARIANTS:
                    raise ValueError('Catalog variants exceed source ceiling')
                grouped[identity] = []
            grouped[identity].append(occurrence)

    variants = []; ids = {}; domains = {field: {} for field in _IDENTITY_FIELDS}
    for identity, occurrences in sorted(grouped.items()):
        clock()
        index = len(variants)
        row = dict(zip(('scene_id', *_IDENTITY_FIELDS), identity))
        row['occurrences'] = sorted(occurrences, key=lambda value: (
            value['repository'], value['commit'], value['root_tree'], value['path'],
            value['oid'], value['pointer']))
        variants.append(row)
        ids.setdefault(row['scene_id'], []).append(index)
        for field in _IDENTITY_FIELDS:
            domains[field].setdefault(row[field], []).append(index)
    id_variants = [{'scene_id': scene_id, 'variant_indices': indices}
                   for scene_id, indices in sorted(ids.items()) if len(indices) > 1]
    aliases = [{'field': field, 'sha256': digest, 'variant_indices': indices}
               for field in _IDENTITY_FIELDS
               for digest, indices in sorted(domains[field].items()) if len(indices) > 1]
    result = {'kind': 'puck-task-catalog-occurrences-v1', 'version': 1,
              'variants': variants, 'id_variants': id_variants, 'identity_aliases': aliases,
              'legacy_scene_rows_compatible': not id_variants and not aliases,
              'document_occurrences': len(documents), 'scene_occurrences': occurrence_count,
              'input_bytes': input_bytes, 'held_out_catalog_read': exposed,
              'inventory_complete': False, 'source_closure_authenticated': False,
              'held_out_runtime_opened': False, 'reservation_authorized': False,
              'collection_authorized': False, 'executable': False, 'qualification_claims': []}
    clock()
    if len(_canonical(result)) > _MAX_OCCURRENCE_METADATA_BYTES:
        raise ValueError('Catalog receipt exceeds source metadata ceiling')
    clock()
    return result
