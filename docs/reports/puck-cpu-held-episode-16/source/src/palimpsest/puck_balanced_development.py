"""Fixed balanced development identity; historical scientific arithmetic unchanged."""
import copy
import hashlib
import math
from pathlib import Path

from . import puck_balanced_student as student, puck_learning as learning, puck_profile as puck
from .artifacts import _json, _read, _safe_path
from .snapshots import read_snapshot, state_digest

PROTOCOL_PATH='docs/plans/m6-puck-balanced-student-development-v1.json'
PROTOCOL_SHA256='2c97b116d563f2069f2257f0aade5d01c6532e26f7dd0406981980541f4f18f6'


def protocol(root):
    raw=_read(Path(root)/PROTOCOL_PATH,32768)
    if hashlib.sha256(raw).hexdigest()!=PROTOCOL_SHA256:raise ValueError('Development protocol differs')
    spec=_json(raw);base=student.protocol(root)
    if (spec['student_contract']['sha256']!=student.PROTOCOL_SHA256 or
            spec['learning_protocol_sha256']!=learning.PROTOCOL_SHA256 or spec['models_manifest']!=base['models_manifest'] or
            hashlib.sha256(_read(Path(root)/'src/palimpsest/puck_balanced_student.py',128*1024)).hexdigest()!=spec['student_contract']['source_sha256']):
        raise ValueError('Development controller/learning/model pins differ')
    for key in ('historical_development','scientific_source','training_objective'):
        pin=spec[key]
        if hashlib.sha256(_read(Path(root)/pin['path'],128*1024)).hexdigest()!=pin['sha256']:
            raise ValueError('Balanced development historical/scientific/objective pin differs')
    return spec


def plan(root):
    spec=protocol(root)
    return [{'id':f'student-dev-{scene}-seed{seed}','case':f'student-dev-{scene}-seed{seed}',
             'kind':'root','seed':scene,'split':spec['layout_split'],'model_seed':seed,
             'max_ticks':spec['max_ticks'],'max_bytes':spec['limits']['owner_bytes']}
            for scene in spec['scene_order'] for seed in spec['model_order']]


def admit_config(config,root):
    row=config.get('row');output=_safe_path(config['output'])
    if (set(config)!={'repo','output','row','sources','learning_student_balanced_development','bundle_root','initial_reference'} or
            config['learning_student_balanced_development']!=PROTOCOL_SHA256 or
            type(row) is not dict or state_digest(row) not in {state_digest(r) for r in plan(root)} or
            output.name!=row['id'] or any((output/n).exists() for n in ('recording','initial.snp','result.json'))):
        raise ValueError('Exact fresh-only development envelope required')
    reference=config['initial_reference']
    if row['model_seed']==21:
        if reference is not None:raise ValueError('First model must establish its own scene baseline')
    elif (type(reference) is not dict or set(reference)!={'owner_id','result_sha256','snapshot_sha256'} or
            reference['owner_id']!=f"student-dev-{row['seed']}-seed21" or
            any(type(reference[k]) is not str or len(reference[k])!=64 or any(c not in '0123456789abcdef' for c in reference[k])
                for k in ('result_sha256','snapshot_sha256'))):
        raise ValueError('Same-scene model21 baseline receipt required')
    student.admit_bundle(root,config['bundle_root'],row['model_seed'])
    return {**puck.layout(root,row['seed'],row['split']),'id':row['case'],'ticks':600}


def application(root,row,sources,profile,model_hash,model,state,world,contact,cursor):
    app=student.application(root,row,sources,profile,model_hash,model,state,world,contact,cursor)
    app.update(kind='puck-balanced-student-development-application-v1',development_protocol_sha256=PROTOCOL_SHA256)
    return app


def validate_initial(app,root,row,sources,profile,model_hash,model):
    if (type(app) is not dict or app.get('kind')!='puck-balanced-student-development-application-v1' or
            app.get('development_protocol_sha256')!=PROTOCOL_SHA256):
        raise ValueError('Development initial application identity differs')
    base=copy.deepcopy(app);base.pop('development_protocol_sha256');base['kind']='puck-balanced-student-application-v1'
    student.validate_application(base,root,row,sources,profile,model_hash,model,0,state_digest(base))
    case=puck.layout(root,row['seed'],row['split']);world=app['world']
    x,y,yaw=case['rover_pose'];qw,qz=math.cos(yaw/2),math.sin(yaw/2)
    pose=[x,y,math.atan2(2*(qw*qz),1-2*(qz*qz))]
    if (world!={'time_s':0.,'rover_pose':pose,'puck_xyz':[*case['puck_xy'],.062],
                'puck_velocity_xy':[0.,0.],'goal_xy':case['goal_xy']} or app['own_supervisor_cursor']!=learning.initial_cursor()):
        raise ValueError('Development authored reset differs')


def scientific_initial(snapshot,root,row,sources,model):
    """Hash defined physical/input/RNG fields; retain raw SNPs without rewriting."""
    import numpy as np
    app=snapshot['application'];validate_initial(app,root,row,sources,app['profile_identity'],app['model_sha256'],model)
    spec=protocol(root);value=snapshot.get('integration');rng=snapshot.get('rng')
    if (snapshot.get('schema_version')!=1 or type(snapshot.get('integration_enum')) is not int or
            snapshot['integration_enum']!=spec['initialization']['integration_enum'] or
            not isinstance(value,np.ndarray) or value.dtype!=np.float64 or value.shape!=(440,) or not np.isfinite(value).all() or
            type(rng) is not dict or set(rng)!={'python','numpy','environment','environment_seed','spaces','torch_cpu','torch_cuda'} or
            type(rng['environment_seed']) is not int or rng['environment_seed']!=row['seed'] or
            type(snapshot.get('native_data')) is not bytes or
            hashlib.sha256(snapshot['native_data']).hexdigest()!=snapshot.get('native_sha256') or
            snapshot.get('policy') is not None or snapshot.get('teacher') is not None):
        raise ValueError('Development native state/RNG schema differs')
    identity=snapshot['identity']
    if (identity.get('mujoco')!=spec['runtime']['mujoco'] or identity.get('numpy')!=spec['runtime']['numpy'] or
            identity.get('python')!=[3,11,15] or identity.get('policy') is not None or identity.get('teacher') is not None or
            not isinstance(identity.get('torch'),dict) or identity['torch'].get('threads')!=1):
        raise ValueError('Development native runtime identity differs')
    state=copy.deepcopy(app['state']);state.pop('episode_id')
    fields={'native_identity':identity,'full_model_sha256':app['model_sha256'],'profile':app['profile_identity'],
            'integration':value,'environment':snapshot['environment'],'world':app['world'],'contact':app['contact'],
            'task':state,'sensors8':app['inputs'],'inputs9':learning.prepare(app['inputs'],app['own_supervisor_cursor'])['inputs'],
            'own_cursor':app['own_supervisor_cursor'],'rng':{k:v for k,v in rng.items() if k not in ('torch_cpu','torch_cuda')}}
    hashes={key:state_digest(value) for key,value in fields.items()}
    return {'sha256':state_digest(hashes),'fields':hashes}


def initial_match(snapshot,config,root,model):
    """Called after saving current initial SNP and strictly before first prediction."""
    row=config['row'];current=scientific_initial(snapshot,root,row,config['sources'],model)
    receipt={'status':'passed','fingerprint':current,'reference':copy.deepcopy(config['initial_reference'])}
    if row['model_seed']==21:return receipt
    reference=config['initial_reference'];source=_safe_path(config['output']).parent/reference['owner_id']
    raw=_read(source/'result.json',4*1024**2)
    if hashlib.sha256(raw).hexdigest()!=reference['result_sha256']:raise ValueError('Development baseline result changed')
    result=_json(raw);baseline=next(r for r in plan(root) if r['id']==reference['owner_id'])
    if (result.get('status')!='passed' or state_digest(result.get('row'))!=state_digest(baseline) or
            result.get('initial_match',{}).get('status')!='passed' or
            set(result.get('snapshots',{}))!={'initial'} or result['snapshots']['initial']['sha256']!=reference['snapshot_sha256']):
        raise ValueError('Development baseline completion/receipt differs')
    path=source/'initial.snp';raw=_read(path,8*1024**2)
    if hashlib.sha256(raw).hexdigest()!=reference['snapshot_sha256']:raise ValueError('Development baseline snapshot changed')
    _,base_model=student.admit_bundle(root,config['bundle_root'],21)
    expected=scientific_initial(read_snapshot(path),root,baseline,config['sources'],base_model)
    if expected!=result['initial_match']['fingerprint']:raise ValueError('Development baseline scientific receipt differs')
    receipt.update(expected_fingerprint=expected,status='passed' if current==expected else 'failed')
    return receipt


def admission(owners,root):
    rows=plan(root)
    if (len(owners)!=len(rows) or any(any(state_digest(item.get(k))!=state_digest(v) for k,v in row.items()) or
            item.get('status')!='completed' for item,row in zip(owners,rows))):
        raise ValueError('Development requires every fixed completed owner')
    counts={str(seed):sum(item['result']['final_state']['reason']=='puck_goal' for item in owners if item['model_seed']==seed)
            for seed in protocol(root)['model_order']}
    return {'status':'passed' if all(n>=3 for n in counts.values()) else 'failed','goals_each_model':counts,
            'required_each_model':3,'held_out':'locked_pending_independent_review_and_explicit_GO'}
