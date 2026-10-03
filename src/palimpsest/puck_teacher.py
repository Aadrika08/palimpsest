"""Fixed teacher-only collection adapter; no learner or restore admission."""
import copy
import hashlib
from pathlib import Path

from . import puck_learning as learning
from . import puck_profile as puck
from .artifacts import _read
from .snapshots import state_digest


def identity(root):
    spec=learning.load_protocol(root)
    return {'learning_protocol_sha256':learning.PROTOCOL_SHA256,
            'pushing_protocol_sha256':puck.PROTOCOL_SHA256,
            'teacher_source_sha256':spec['teacher_source_sha256'],
            'supervisor_source_sha256':hashlib.sha256(_read(Path(root)/'src/palimpsest/puck_learning.py',128*1024)).hexdigest(),
            'learning_feature_id':spec['learning_feature_id'],'teacher_id':spec['teacher_id']}


def plan(root):
    spec=learning.load_protocol(root)
    rows=[{'id':f"teacher-{item['seed']}",'case':f"teacher-{item['seed']}",'kind':'root',
           'seed':item['seed'],'split':item['split'],'max_ticks':600,
           'max_bytes':spec['limits']['per_600_tick_record_and_snapshot_bytes']}
          for item in spec['layouts'] if item['split'] in ('train','recorded_dev')]
    if len(rows)!=20 or [r['seed'] for r in rows]!=list(range(6000,6020)):
        raise ValueError('Fixed teacher collection rows differ')
    return rows


def admit_config(config,root):
    if (set(config)!={'repo','output','row','sources','learning_teacher'} or
            config['learning_teacher']!=learning.PROTOCOL_SHA256 or
            type(config['row']) is not dict or
            state_digest(config['row']) not in {state_digest(row) for row in plan(root)} or
            Path(config['output']).name!=config['row']['id']):
        raise ValueError('Learning teacher requires exact fresh-only configuration; no restore/replay')
    row=config['row']
    if any((Path(config['output'])/name).exists() for name in ('recording','initial.snp','result.json')):
        raise ValueError('Teacher owner output is not fresh')
    layout=puck.layout(root,row['seed'],row['split'])
    return {**layout,'id':row['case'],'ticks':600}


class SensorModeDisagreement(ValueError):
    def __init__(self,evidence):
        super().__init__('Teacher and independent sensor-only supervisor disagree before control')
        self.evidence=evidence


def decide(inputs,world,teacher_mode,own):
    """Call the privileged expert once; never seed the own cursor from it."""
    import numpy as np
    action,next_mode=puck.demonstrate(world,teacher_mode)
    pending=learning.prepare(inputs,own)
    if teacher_mode!=own['mode'] or next_mode!=pending['after']['mode']:
        raise SensorModeDisagreement({'episode':0,'completed_tick':own['tick'],'executed_interval':False,
            'inputs':{'dtype':inputs.dtype.str,'shape':list(inputs.shape),'bytes_hex':inputs.tobytes().hex()},
            'expert_action':{'dtype':'<f8','shape':[2],'bytes_hex':np.asarray(action,np.float64).tobytes().hex()},
            'teacher_mode_before':teacher_mode,'teacher_mode_after':next_mode,
            'supervisor_mode_before':own['mode'],'supervisor_mode_after':pending['after']['mode']})
    return action,next_mode,pending


def initial_application(root,row,sources,profile,model_hash,state,world,contact,own):
    app={'version':1,'kind':'puck-teacher-initial-v1',**identity(root),'case':row['case'],
         'seed':row['seed'],'split':row['split'],'source_hashes':copy.deepcopy(sources),
         'profile_identity':copy.deepcopy(profile),'model_sha256':model_hash,'state':copy.deepcopy(state),
         'world':copy.deepcopy(world),'contact':copy.deepcopy(contact),'inputs':puck.project(world,contact),
         'teacher_mode':'approach','own_supervisor_cursor':copy.deepcopy(own),'paused':True}
    validate_initial(app,root,row,sources,profile,model_hash,state_digest(app))
    return app


def validate_initial(app,root,row,sources,profile,model_hash,expected_hash):
    import numpy as np
    required={'version','kind','case','seed','split','source_hashes','profile_identity','model_sha256',
              'state','world','contact','inputs','teacher_mode','own_supervisor_cursor','paused',*identity(root)}
    if (type(app) is not dict or set(app)!=required or type(app['version']) is not int or app['version']!=1 or
            app['kind']!='puck-teacher-initial-v1' or app['paused'] is not True or
            state_digest(app)!=expected_hash or any(app.get(k)!=v for k,v in identity(root).items()) or
            app['case']!=row['case'] or type(app['seed']) is not int or app['seed']!=row['seed'] or
            app['split']!=row['split'] or app['source_hashes']!=sources or app['profile_identity']!=profile or
            app['model_sha256']!=model_hash or app['teacher_mode']!='approach' or
            learning.validate_cursor(app['own_supervisor_cursor'])!=learning.initial_cursor()):
        raise ValueError('Teacher initial-only snapshot identity differs; restore/replay not admitted')
    world,contact=app['world'],app['contact']
    expected_state=puck.initialize(world,row['case'])
    expected_inputs=puck.project(world,contact)
    if (world['time_s']!=0. or app['state']!=expected_state or contact['tick']!=0 or
            not isinstance(app['inputs'],np.ndarray) or app['inputs'].dtype!=np.float32 or
            app['inputs'].shape!=(8,) or app['inputs'].tobytes()!=expected_inputs.tobytes()):
        raise ValueError('Teacher initial snapshot cursor/projection differs')
