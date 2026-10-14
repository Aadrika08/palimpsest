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
