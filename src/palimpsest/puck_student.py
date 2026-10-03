"""Fixed headless research student; sensors and own phase only at inference."""
import copy
import hashlib
import math
from pathlib import Path

from . import puck_learning as learning, puck_model, puck_profile as puck
from .artifacts import _json, _read, _safe_path
from .snapshots import state_digest

PROTOCOL_PATH='docs/plans/m6-puck-student-mechanism-v1.json'
PROTOCOL_SHA256='72a2d8c3c496e7f9c9bfe21f68c581795dd00795507c7b7660a1156b7df5c968'


def protocol(root):
    raw=_read(Path(root)/PROTOCOL_PATH,32768)
    if hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA256:
        raise ValueError('Student mechanism protocol differs')
    spec=_json(raw);learning.load_protocol(root)
    if spec['learning_protocol_sha256']!=learning.PROTOCOL_SHA256:
        raise ValueError('Student learning identity differs')
    for item in (spec['models_manifest'],spec['native_mechanics_protocol']):
        if hashlib.sha256(_read(Path(root)/item['path'],32768)).hexdigest()!=item['sha256']:
            raise ValueError('Pinned student manifest/native protocol differs')
    return spec


def plan(root):
    spec=protocol(root);case='student-6000-seed21'
    common={'case':case,'seed':6000,'split':'train','model_seed':21}
    return [{'id':case,'kind':'root',**common,'max_ticks':120,'max_bytes':64*1024**2}]+[
        {**row,**common,'max_bytes':32*1024**2 if row['kind']=='native-continuation' else 64*1024**2}
        for row in spec['derivatives']]


def model_entry(root,seed):
    spec=protocol(root)
    manifest=_json(_read(Path(root)/spec['models_manifest']['path'],32768))
    if type(seed) is not int or seed not in (21,22,23):
        raise ValueError('Unknown fixed student model')
    return next(row for row in manifest['models'] if row['seed']==seed)


def admit_bundle(root,bundle_root,seed):
    entry=model_entry(root,seed);directory=_safe_path(bundle_root)/entry['directory']
    for name,pin in entry['files'].items():
        cap=puck_model.MAX_CHECKPOINT if name.endswith('.npz') else 4*1024**2
        if hashlib.sha256(_read(directory/name,cap)).hexdigest()!=pin:
            raise ValueError('Student model artifact pin differs: '+name)
    _,identity=puck_model.read_bundle(directory,entry['files']['report.json'],root,seed)
    return directory,identity


def load(root,bundle_root,seed):
    directory,expected=admit_bundle(root,bundle_root,seed)
    model,actual=puck_model.load_model(directory,expected['training_report_sha256'],root,seed)
    if actual!=expected:raise ValueError('Student bundle changed while loading')
    return model,actual


def check_parameters(model,root,bundle_root,seed):
    directory,identity=admit_bundle(root,bundle_root,seed)
    expected=puck_model.read_checkpoint(_read(directory/'checkpoint.npz',puck_model.MAX_CHECKPOINT))
    actual=puck_model.validate_arrays({name:value.detach().cpu().numpy() for name,value in model.state_dict().items()})
    if any(actual[name].tobytes()!=expected[name].tobytes() for name in expected):
        raise ValueError('Live student parameters differ from frozen checkpoint')
    return identity


def identity(root,model):
    spec=protocol(root);entry=model_entry(root,model.get('training_seed'))
    expected={'training_seed':entry['seed'],'training_report_sha256':entry['files']['report.json'],
        'checkpoint_sha256':entry['files']['checkpoint.npz'],'protocol_sha256':entry['files']['protocol.json'],
        'learning_protocol_sha256':learning.PROTOCOL_SHA256,
        'supervisor_source_sha256':hashlib.sha256(_read(Path(root)/'src/palimpsest/puck_learning.py',128*1024)).hexdigest()}
    if state_digest(model)!=state_digest(expected):raise ValueError('Student model identity differs')
    return {'student_protocol_sha256':PROTOCOL_SHA256,'learning_protocol_sha256':learning.PROTOCOL_SHA256,
        'pushing_protocol_sha256':puck.PROTOCOL_SHA256,'models_manifest_sha256':spec['models_manifest']['sha256'],
        'learning_feature_id':learning.load_protocol(root)['learning_feature_id'],
        'supervisor_source_sha256':expected['supervisor_source_sha256'],
        'student_source_sha256':hashlib.sha256(_read(Path(root)/'src/palimpsest/puck_student.py',128*1024)).hexdigest(),
        'model_identity':copy.deepcopy(expected)}


def admit_config(config,root):
    common={'repo','output','row','sources','learning_student','bundle_root'}
    row=config.get('row')
    if (type(row) is not dict or state_digest(row) not in {state_digest(r) for r in plan(root)} or
            config.get('learning_student')!=PROTOCOL_SHA256 or 'learning_teacher' in config):
        raise ValueError('Exact fixed student mechanism envelope required')
    extra=set() if row['kind']=='root' else {'source_output','source_snapshot','start_tick','ticks'}
    output=_safe_path(config['output'])
    if set(config)!=common|extra or output.name!=row['id']:
        raise ValueError('Student configuration fields/path differ')
    if any((output/name).exists() for name in ('recording','initial.snp','result.json')):
        raise ValueError('Student output is not fresh')
    if extra:
        start,count=config['start_tick'],config['ticks']
        valid=(type(start) is int and type(count) is int and
               ((start,count)==(1,4) if row['kind']=='native-continuation' else start==0 and 5<=count<=120))
        if not valid:
            raise ValueError('Student source window differs from fixed plan')
        if _safe_path(config['source_output'])!=output.parent/row['case']:
            raise ValueError('Student derivative requires its same-gate source owner')
        receipt=config['source_snapshot']
        if (type(receipt) is not dict or set(receipt)!={'file','sha256','bytes','tick','application_sha256','world','contact'} or
                receipt['file']!=row['boundary']+'.snp' or type(receipt['tick']) is not int or receipt['tick']!=start or
                type(receipt['bytes']) is not int or not 0<receipt['bytes']<=8*1024**2 or
                any(type(receipt[k]) is not str or len(receipt[k])!=64 or any(c not in '0123456789abcdef' for c in receipt[k])
                    for k in ('sha256','application_sha256'))):
            raise ValueError('Student source snapshot receipt differs')
    admit_bundle(root,config['bundle_root'],row['model_seed'])
    return {**puck.layout(root,6000,'train'),'id':row['case'],'ticks':120}


def action(value):
    import numpy as np
    if (not isinstance(value,np.ndarray) or value.dtype!=np.float64 or value.shape!=(2,) or
            not np.isfinite(value).all() or np.any(np.abs(value)>.4)):
        raise ValueError('Student action must be finite float64[2] within exact task bounds')
    return value.copy()


def decide(sensors,cursor,model,recorded=None):
    """Stage own mode and one model output; no private world or expert argument."""
    import numpy as np
    pending=learning.prepare(sensors,cursor)
    if recorded is None:
        output=action(puck_model.predict(model,pending['inputs']))
    else:
        for key,expected in (('inputs',sensors),('student_inputs',pending['inputs'])):
            value=np.asarray(recorded.get(key))
            if value.dtype!=expected.dtype or value.shape!=expected.shape or value.tobytes()!=expected.tobytes():
                raise ValueError('Action replay input differs')
        for key,which in (('supervisor_mode_before','before'),('supervisor_mode_after','after')):
            learning._mode(recorded.get(key),learning.MODES[pending[which]['mode']])
        if any(key.startswith('teacher') for key in recorded):raise ValueError('Teacher record is not student replay')
        output=action(recorded.get('action'))
    return output,pending


def application(root,row,sources,profile,model_hash,model,state,world,contact,cursor):
    app={'version':1,'kind':'puck-student-application-v1',**identity(root,model),'case':row['case'],
         'seed':row['seed'],'split':row['split'],'source_hashes':copy.deepcopy(sources),
         'profile_identity':copy.deepcopy(profile),'model_sha256':model_hash,'state':copy.deepcopy(state),
         'world':copy.deepcopy(world),'contact':copy.deepcopy(contact),'inputs':puck.project(world,contact),
         'own_supervisor_cursor':learning.validate_cursor(cursor),'paused':True}
    validate_application(app,root,row,sources,profile,model_hash,model,state['tick'],state_digest(app))
    return app


def validate_application(app,root,row,sources,profile,model_hash,model,tick,expected_hash):
    import numpy as np
    pins=identity(root,model)
    required={'version','kind',*pins,'case','seed','split','source_hashes','profile_identity','model_sha256',
              'state','world','contact','inputs','own_supervisor_cursor','paused'}
    if (type(app) is not dict or set(app)!=required or type(app['version']) is not int or app['version']!=1 or
            app['kind']!='puck-student-application-v1' or app['paused'] is not True or state_digest(app)!=expected_hash or
            any(state_digest(app.get(k))!=state_digest(v) for k,v in pins.items()) or app['case']!=row['case'] or
            type(app['seed']) is not int or app['seed']!=row['seed'] or app['split']!=row['split'] or
            state_digest(app['source_hashes'])!=state_digest(sources) or
            state_digest(app['profile_identity'])!=state_digest(profile) or app['model_sha256']!=model_hash):
        raise ValueError('Student snapshot identity/schema differs before native restore')
    cursor=learning.validate_cursor(app['own_supervisor_cursor'])
    state,world,contact=app['state'],app['world'],app['contact']
    puck._world(world);puck._contact(contact,world['time_s'])
    puck._fields(state,('version','protocol_sha256','episode_id','tick','initial_puck_xy','previous_puck_xy',
                       'previous_rover_xy','goal_xy','previous_distance','had_contact','dwell_ticks','stall_ticks','reason'),'student task state')
    puck._version(state['version'])
    for name in ('initial_puck_xy','previous_puck_xy','previous_rover_xy','goal_xy'):
        if any(abs(v)>5 for v in puck._pair(state[name],name)):raise ValueError('Student task position differs')
    if (type(tick) is not int or not 0<=tick<600 or type(state['tick']) is not int or state['tick']!=tick or
            cursor['tick']!=tick or contact['tick']!=tick or not math.isclose(world['time_s'],tick*.02,rel_tol=0.,abs_tol=1e-9) or
            state['protocol_sha256']!=puck.PROTOCOL_SHA256 or state['episode_id']!=row['case'] or state['reason'] is not None or
            state['previous_puck_xy']!=world['puck_xyz'][:2] or state['previous_rover_xy']!=world['rover_pose'][:2] or
            state['goal_xy']!=world['goal_xy'] or state['previous_distance']!=math.dist(world['puck_xyz'][:2],world['goal_xy']) or
            type(state['had_contact']) is not bool or type(state['dwell_ticks']) is not int or not 0<=state['dwell_ticks']<=min(tick,9) or
            type(state['stall_ticks']) is not int or not 0<=state['stall_ticks']<=min(tick,99) or state['dwell_ticks'] and not state['had_contact']):
        raise ValueError('Student snapshot task/contact/own cursor differs')
    if tick==0 and state!=puck.initialize(world,row['case']):raise ValueError('Student initial state differs')
    expected=puck.project(world,contact);value=app['inputs']
    if not isinstance(value,np.ndarray) or value.dtype!=np.float32 or value.shape!=(8,) or value.tobytes()!=expected.tobytes():
        raise ValueError('Student snapshot sensor projection differs')


def admit_source(manifest,root,row,sources,model):
    if (manifest.get('schema')!='puck-student-v1' or manifest.get('status')!='completed' or
            state_digest(manifest.get('source_hashes'))!=state_digest(sources) or
            state_digest(manifest.get('row'))!=state_digest(plan(root)[0]) or
            any(state_digest(manifest.get(k))!=state_digest(v) for k,v in identity(root,model).items())):
        raise ValueError('Student derivative source recording identity differs')
    count=manifest.get('recorded_ticks')
    if type(count) is not int or not 5<=count<=120:raise ValueError('Student source lacks fixed successor coverage')
    return count
