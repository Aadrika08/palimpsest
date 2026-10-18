"""Pure ninth-input supervisor and teacher-data admission; no model/native runtime.

The MLP remains prospective. This module never imports the privileged teacher or
reads world geometry at inference. Native outcome/snapshot qualification remains
the separately supervised collector's responsibility, not a claim of this reader.
"""
import copy
import hashlib
import math
from pathlib import Path

from .artifacts import _events, _fingerprint, _json, _read, _safe_path
from .records import iter_ticks
from .storage import StorageBudget, StorageLimits

PROTOCOL_PATH='docs/plans/m6-puck-learning-v2.json'
PROTOCOL_SHA256='bfdd047c1763af3d0b254c55df9137e179b65ce99e7eb870ca76f41332a83354'
MODES={'approach':0,'push':1}
MAX_TICKS=600


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def load_protocol(repo_root):
    root=Path(repo_root)
    raw=_read(root/PROTOCOL_PATH,128*1024)
    if _sha(raw)!=PROTOCOL_SHA256:
        raise ValueError('Puck learning protocol pin differs')
    spec=_json(raw)
    task=spec['task_protocol']
    task_raw=_read(root/task['path'],128*1024)
    if (_sha(task_raw)!=task['sha256'] or
            _sha(_read(root/'src/palimpsest/puck_profile.py',128*1024))!=spec['teacher_source_sha256']):
        raise ValueError('Frozen task/teacher source differs')
    task=_json(task_raw)
    return spec | {key:task[key] for key in ('layouts','limits','observation')} | {
        'learning':task['learning'] | spec['learning'], 'admission':task['admission'] | spec['admission']}


def initial_cursor():
    return {'version':1,'protocol_sha256':PROTOCOL_SHA256,'tick':0,'mode':'approach'}


def validate_cursor(cursor):
    if (type(cursor) is not dict or set(cursor)!={'version','protocol_sha256','tick','mode'} or
            type(cursor['version']) is not int or cursor['version']!=1 or
            cursor['protocol_sha256']!=PROTOCOL_SHA256 or type(cursor['tick']) is not int or
            not 0<=cursor['tick']<=MAX_TICKS or type(cursor['mode']) is not str or
            cursor['mode'] not in MODES or cursor['tick']==0 and cursor['mode']!='approach'):
        raise ValueError('Invalid puck supervisor cursor')
    return copy.deepcopy(cursor)


def _sensors(values):
    import numpy as np
    if (not isinstance(values,np.ndarray) or values.dtype!=np.float32 or values.shape!=(8,) or
            not np.isfinite(values).all() or np.any(np.abs(values)>1) or
            values[6] not in (0.,1.) or values[7]!=0.):
        raise ValueError('Expected finite bounded float32[8] sensors and valid contact flags')
    return values.copy()


def prepare(sensors,cursor):
    """Stage one decision without changing the caller's own completed cursor."""
    import numpy as np
    before=validate_cursor(cursor)
    if before['tick']==MAX_TICKS:
        raise ValueError('Puck episode budget exhausted')
    values=_sensors(sensors)
    px,py,gx,gy=map(float,values[:4].astype(np.float64)*14.)
    dx,dy=gx-px,gy-py
    distance=math.hypot(dx,dy)
    mode=before['mode']
    # Stop is evaluated before division, including coincident puck and goal.
    if distance>.2:
        ux,uy=dx/distance,dy/distance
        axial=px*ux+py*uy
        lateral=abs(px*uy-py*ux)
        ready=.35<=axial<=.63 and lateral<=.06
        arrival=math.hypot(px-.55*ux,py-.55*uy)<=.08
        if mode=='push' and not ready:
            mode='approach'
        elif mode=='approach' and ready and arrival:
            mode='push'
    inputs=np.concatenate((values,np.array([MODES[before['mode']]],np.float32)))
    return {'before':before,'after':{**before,'tick':before['tick']+1,'mode':mode},
            'inputs':inputs,'sensors_sha256':_sha(values.tobytes())}


def commit(cursor,pending,completed_tick):
    """Return next cursor only after the caller's completed-interval receipt.

    The future native owner must call this after successful step/record staging;
    no function here mutates a live cursor or asserts that a physics step happened.
    """
    import numpy as np
    before=validate_cursor(cursor)
    if (type(pending) is not dict or set(pending)!={'before','after','inputs','sensors_sha256'} or
            pending['before']!=before or type(completed_tick) is not int or completed_tick!=before['tick']+1):
        raise ValueError('Supervisor predecessor/completed tick differs')
    validate_cursor(pending['before']);validate_cursor(pending['after'])
    inputs=pending['inputs']
    if not isinstance(inputs,np.ndarray) or inputs.dtype!=np.float32 or inputs.shape!=(9,):
        raise ValueError('Staged nine-input vector differs')
    expected=prepare(inputs[:8],before)
    if (pending['after']!=expected['after'] or pending['sensors_sha256']!=expected['sensors_sha256'] or
            inputs.tobytes()!=expected['inputs'].tobytes()):
        raise ValueError('Staged supervisor input/candidate changed')
    return validate_cursor(expected['after'])


def _mode(value,expected):
    import numpy as np
    array=np.asarray(value)
    if array.dtype!=np.uint8 or array.shape!=() or array.item()!=expected:
        raise ValueError('Recorded teacher/supervisor mode disagrees with sensor-only cursor')


def scale_action(normalized):
    """One declared float32 tanh -> float64 command boundary; never clip."""
    import numpy as np
    if (not isinstance(normalized,np.ndarray) or normalized.dtype!=np.float32 or normalized.shape!=(2,) or
            not np.isfinite(normalized).all() or np.any(np.abs(normalized)>1)):
        raise ValueError('Expected finite bounded float32[2] normalized action')
    return normalized.astype(np.float64)*np.float64(.4)


def admit_teacher_rows(rows,expected_ticks):
    """Reconstruct from reset; no recorded teacher state seeds the own cursor."""
    import numpy as np
    if type(expected_ticks) is not int or not 1<=expected_ticks<=MAX_TICKS:
        raise ValueError('Invalid bounded teacher tick count')
    own=initial_cursor();inputs=[];targets=[]
    for index,row in enumerate(rows):
        if (type(row) is not dict or index>=expected_ticks or type(row.get('episode')) is not int or row['episode']!=0 or
                type(row.get('tick')) is not int or row['tick']!=index):
            raise ValueError('Teacher data must be one bounded contiguous episode from reset')
        pending=prepare(row.get('inputs'),own)
        before,after=MODES[own['mode']],MODES[pending['after']['mode']]
        for name,code in [('teacher_mode_before',before+1),('teacher_mode_after',after+1),
                          ('supervisor_mode_before',before),('supervisor_mode_after',after)]:
            _mode(row.get(name),code)
        supplied=np.asarray(row.get('student_inputs'))
        if supplied.dtype!=np.float32 or supplied.shape!=(9,) or supplied.tobytes()!=pending['inputs'].tobytes():
            raise ValueError('Recorded ninth input differs from independent BEFORE-mode')
        label=np.asarray(row.get('action'))
        if label.dtype!=np.float64 or label.shape!=(2,) or not np.isfinite(label).all() or np.any(np.abs(label)>.4):
            raise ValueError('Teacher action label has wrong dtype, shape or finite bounds')
        inputs.append(pending['inputs']);targets.append(label.copy())
        own=commit(own,pending,index+1)
    if len(inputs)!=expected_ticks:
        raise ValueError('Teacher recording ended before declared tick count')
    return {'inputs':np.stack(inputs),'targets':np.stack(targets),'final_cursor':own}


def admit_record(path,manifest_sha256,seed,split,repo_root):
    """Admit bounded completed recording data; preserve files on every failure.

    This checks sensor/mode/label and recorded outcome contracts. It does not
    independently prove that the recorded native contact/task outcome occurred.
    A reviewed collector plus native artifact audit remains a separate gate.
    """
    import numpy as np
    spec=load_protocol(repo_root);path=_safe_path(path)
    if path.name!='recording' or type(seed) is not int or split not in ('train','recorded_dev') or not any(
            row['seed']==seed and row['split']==split for row in spec['layouts']):
        raise ValueError('Unknown teacher layout/split or recording path')
    limit=spec['limits']['per_600_tick_record_and_snapshot_bytes']
    usage=StorageBudget((path.parent,),StorageLimits(max_bytes=limit,min_free_bytes=0)).usage()
    if usage['used_bytes']>limit:
        raise ValueError('Teacher owner files exceed 160 MiB admission cap')
    paths=[path/'manifest.json',path/'events.jsonl',*sorted((path/'chunks').glob('*.npz'))]
    if len(paths)>21:
        raise ValueError('Teacher recording exceeds bounded chunk count')
    fingerprint=_fingerprint(paths)
    raw=_read(paths[0],1024**2)
    if type(manifest_sha256) is not str or _sha(raw)!=manifest_sha256:
        raise ValueError('Teacher manifest pin differs')
    manifest=_json(raw)
    expected={'schema':'puck-demonstration-v1','learning_protocol_sha256':PROTOCOL_SHA256,
              'pushing_protocol_sha256':spec['task_protocol']['sha256'],
              'teacher_source_sha256':spec['teacher_source_sha256'],'teacher_id':spec['teacher_id'],
              'supervisor_source_sha256':_sha(_read(Path(repo_root)/'src/palimpsest/puck_learning.py',128*1024)),
              'learning_feature_id':spec['learning_feature_id'],
              'seed':seed,'split':split,'episodes':1,'status':'completed','outcome':'puck_goal',
              'initial_supervisor':initial_cursor()}
    if any(manifest.get(k)!=v or type(manifest.get(k)) is not type(v) for k,v in expected.items()):
        raise ValueError('Teacher provenance/reset/completed outcome differs')
    validate_cursor(manifest['initial_supervisor'])
    count=manifest.get('recorded_ticks')
    if type(count) is not int or not (32 if split=='train' else 1)<=count<=MAX_TICKS:
        raise ValueError('Insufficient or oversized fixed teacher episode')
    events=_events(path.parent)
    starts=[e for e in events if e['kind']=='episode_start']
    if (len(starts)!=1 or type(starts[0].get('episode')) is not int or starts[0]['episode']!=0 or
            type(starts[0].get('seed')) is not int or starts[0]['seed']!=seed or
            starts[0].get('teacher_mode')!='approach' or starts[0].get('supervisor_cursor')!=initial_cursor()):
        raise ValueError('Teacher episode start/reset differs')
    validate_cursor(starts[0]['supervisor_cursor'])
    intervals=[e for e in events if e['kind']=='puck_interval']
    chunk_paths=[path/e['path'] for e in events if e['kind']=='chunk']
    # iter_ticks validates each declared path/hash/schema before yielding any row.
    rows=[]
    for row in iter_ticks(path):
        if len(rows)>=MAX_TICKS:
            raise ValueError('Too many teacher rows')
        rows.append(row)
    if sorted(chunk_paths)!=paths[2:] or len(intervals)!=count:
        raise ValueError('Unindexed chunks or incomplete teacher interval events')
    contacts=0;previous_dwell=0
    for tick,event in enumerate(intervals,1):
        state,contact=event.get('state',{}),event.get('contact',{})
        if (type(state) is not dict or type(contact) is not dict or
                not {'tick','reason','dwell_ticks'}<=state.keys() or not {'tick','rover_puck_contact','failure'}<=contact.keys() or
                type(state.get('dwell_ticks')) is not int or not 0<=state['dwell_ticks']<=10 or
                type(state.get('tick')) is not int or state['tick']!=tick or type(contact.get('tick')) is not int or
                contact['tick']!=tick or type(contact.get('rover_puck_contact')) is not bool or
                contact.get('failure') is not None or state.get('reason')!=('puck_goal' if tick==count else None)):
            raise ValueError('Teacher interval/outcome/contact cursor differs')
        contacts+=contact['rover_puck_contact']
        dwell=state['dwell_ticks']
        if dwell and dwell!=previous_dwell+1 or dwell==10 and tick!=count:
            raise ValueError('Recorded dwell counter or terminal boundary differs')
        previous_dwell=dwell
    if not intervals or type(intervals[-1]['state'].get('dwell_ticks')) is not int or intervals[-1]['state']['dwell_ticks']!=10:
        raise ValueError('Teacher lacks recorded ten-tick goal dwell')
    result=admit_teacher_rows(rows,count)
    for row,event in zip(rows,intervals):
        for role,offset in (('teacher',1),('supervisor',0)):
            for position in ('before','after'):
                name=f'{role}_mode_{position}'
                if type(event.get(name)) is not str or event[name] not in MODES or MODES[event[name]]+offset!=int(row[name]):
                    raise ValueError('Recorded numeric/event mode differs')
    stop_labels=0
    for row in reversed(rows):
        if not np.array_equal(row['action'],np.zeros(2,np.float64)):break
        stop_labels+=1
    if split=='train' and (contacts<10 or stop_labels<10):
        raise ValueError('Teacher lacks fixed contact/terminal-stop coverage')
    source_hashes={}
    for source in paths:
        with source.open('rb') as stream:
            source_hashes[str(source.relative_to(path))]=hashlib.file_digest(stream,'sha256').hexdigest()
    if _fingerprint(paths)!=fingerprint:
        raise ValueError('Teacher source changed during admission')
    result.update(seed=seed,split=split,ticks=count,contact_intervals=contacts,terminal_stop_labels=stop_labels,
                  manifest_sha256=manifest_sha256,paths=paths,fingerprint=fingerprint,
                  source_hashes=source_hashes,
                  feature_sha256=_sha(result['inputs'].tobytes()),target_sha256=_sha(result['targets'].tobytes()))
    return result


def admit_batch(entries,repo_root):
    """Validate all fixed 20 rows; return no arrays if any row fails admission."""
    spec=load_protocol(repo_root)
    expected=[(r['seed'],r['split']) for r in spec['layouts'] if r['split'] in ('train','recorded_dev')]
    if (type(entries) is not list or len(entries)!=20 or any(type(e) is not dict or
            set(e)!={'seed','split','path','manifest_sha256'} for e in entries) or
            [(e['seed'],e['split']) for e in entries]!=expected):
        raise ValueError('Fixed teacher batch plan/order differs')
    paths=[_safe_path(e['path']) for e in entries]
    if len(set(paths))!=20 or any(a.parent==b.parent for i,a in enumerate(paths) for b in paths[i+1:]):
        raise ValueError('Teacher source owners must be distinct')
    used=StorageBudget(tuple(p.parent for p in paths),StorageLimits(max_bytes=spec['limits']['teacher']['bytes'],min_free_bytes=0)).usage()
    if used['used_bytes']>spec['limits']['teacher']['bytes']:
        raise ValueError('Teacher batch exceeds fixed aggregate cap')
    rows=[];data=[]
    for entry in entries:
        row={'seed':entry['seed'],'split':entry['split'],'status':'not_started'};rows.append(row)
        try:
            item=admit_record(entry['path'],entry['manifest_sha256'],entry['seed'],entry['split'],repo_root)
            data.append(item);row.update(status='passed',ticks=item['ticks'])
        except (ValueError,OSError,RuntimeError) as error:
            row.update(status='failed',error=str(error))
    for item in data:
        try:
            if _fingerprint(item['paths'])!=item['fingerprint']:
                raise ValueError('Teacher source changed before batch publication')
        except (ValueError,OSError) as error:
            next(r for r in rows if r['seed']==item['seed']).update(status='failed',error=str(error))
    result={'status':'passed' if all(r['status']=='passed' for r in rows) else 'failed','rows':rows}
    if result['status']=='passed':result['data']=data
    return result
