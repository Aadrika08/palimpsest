"""Durable recording closes, distinct from native/process/study acceptance."""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path

from . import puck_on_policy as p, puck_learning as learning, puck_profile as puck
from .artifacts import _json
from .snapshots import state_digest

MiB=1024**2
_AUTHORITY={'native_authorized':False,'collection_authorized':False,
            'fitting_authorized':False,'executable':False,'qualification_claims':[]}
_OWNER_FIELDS={'version','kind','lineage_sha256','owner','scene','recording_path',
    'execution_freeze_sha256','reservation_sha256','status','intervals','commitments',
    'recording_bytes','terminal_reason','final_state_sha256','final_cursor',
    'coverage_count',*_AUTHORITY}
_STAGE_FIELDS={'version','kind','lineage_sha256','execution_freeze_sha256',
    'reservation_sha256','status','owners','intervals','coverage_by_model',*_AUTHORITY}


def _publication(path,name):
    return p._read_publication(path,name,max_manifest_bytes=MiB)


def _owner(value):
    ordinal=value.get('ordinal') if type(value) is dict else None
    if type(ordinal) is not int or not 0<=ordinal<12:
        raise ValueError('Exact collection owner ordinal required')
    scene,seed=6110+ordinal//3,21+ordinal%3
    expected={'ordinal':ordinal,'owner_id':f'collection-{scene}-seed-{seed}',
              'scene_id':scene,'model_seed':seed}
    if p._canonical_bytes(value,'Owner')!=p._canonical_bytes(expected,'Owner'):
        raise ValueError('Fixed collection owner roster differs')
    return expected


def _path(value):
    text=os.fspath(value)
    if (type(text) is not str or not text.startswith('/') or str(Path(text))!=text
            or any(part in ('','.', '..') for part in text.split('/')[1:])
            or '\\' in text or any(ord(c)<32 or ord(c)==127 for c in text)):
        raise ValueError('Exact absolute collection artifact path required')
    return Path(text)


def motivating_condition(inputs, before_mode):
    """Unchanged float32 sensor predicates; no count can steer collection."""
    values=learning._sensors(inputs)
    px,py,gx,gy=map(float,values[:4].astype('float64')*14.)
    dx,dy=gx-px,gy-py;distance=math.hypot(dx,dy)
    if distance<=.2:return False
    ux,uy=dx/distance,dy/distance
    axial=px*ux+py*uy;lateral=abs(px*uy-py*ux)
    return (before_mode=='approach' and values[6]==1 and .35<=axial<=.63
            and lateral<=.06 and math.hypot(px-.55*ux,py-.55*uy)>.08)


def _initial(world,state,scene):
    layout=scene['layout']
    if (world['time_s']!=0. or world['rover_pose']!=layout['rover_pose']
            or world['puck_xyz']!=[*layout['puck_xy'],.062]
            or world['goal_xy']!=layout['goal_xy'] or world['puck_velocity_xy']!=[0.,0.]):
        raise ValueError('Recording scientific initial layout differs')
    if state_digest(puck.initialize(world,state['episode_id']))!=state_digest(state):
        raise ValueError('Recording task initial state differs')


def _recording(path, scene):
    """Stream actual rows, exact namespace and raw commitment chain twice-bound."""
    path=_path(path)
    root,fd,identity=p._open_publication_root(path)
    try:
        names=sorted(os.listdir(fd))
        if not 1<=len(names)<=600 or names!=[f'{n:06d}' for n in range(1,len(names)+1)]:
            raise ValueError('Complete bounded interval namespace required')
        pins=[];previous=None;coverage=0;retained=0;cursor=learning.initial_cursor()
        for item in p.read_committed_intervals(path):
            n=item['completed_tick'];event=item['event'];row=item['row']
            if previous is None:
                _initial(event['world_before'],event['state_before'],scene)
            else:
                if previous['state']['reason'] is not None:
                    raise ValueError('Recording continues after a natural terminal')
                for key,before in (('state','state_before'),('world','world_before'),('contact','contact_before')):
                    if state_digest(previous[key])!=state_digest(event[before]):
                        raise ValueError('Recording episode/state/world/contact continuity differs')
            cursor=learning.commit(cursor,learning.prepare(row['inputs'],cursor),n)
            coverage+=int(motivating_condition(row['inputs'],event['supervisor_mode_before']))
            child=path/f'{n:06d}';_,child_fd,child_identity=p._open_publication_root(child)
            try:
                raw=p._read_exact_file(child,child/'commit.json',8192,'Interval commitment',
                    directory=child_fd,root_identity=child_identity,expected_links=2)
                commit=_json(raw)
                if commit['completed_tick']!=n or commit['previous_commit_sha256']!=(pins[-1]['sha256'] if pins else None):
                    raise ValueError('Recording raw commitment chain differs')
                pins.append({'completed_tick':n,'sha256':p._sha256(raw)})
                retained+=sum(v['bytes'] for v in commit['files'].values())+2*len(raw)
            finally:os.close(child_fd)
            previous=event
        if len(pins)!=len(names):raise ValueError('Uncommitted prefix tail cannot close normally')
        if previous['state']['reason'] is None:
            raise ValueError('Unfinished recording has no natural terminal')
        if retained>149*MiB:raise ValueError('Collection recording exceeds 149 MiB')
        p._verify_publication_root(root,fd,identity)
        if sorted(os.listdir(fd))!=names:raise ValueError('Recording namespace changed during close')
        return {'intervals':len(pins),'commitments':pins,'recording_bytes':retained,
            'terminal_reason':previous['state']['reason'],
            'final_state_sha256':state_digest(previous['state']),
            'final_cursor':cursor,'coverage_count':coverage}
    finally:os.close(fd)


def _same(left,right,label):
    if p._canonical_bytes(left,label)!=p._canonical_bytes(right,label):
        raise ValueError(label+' changed before durable admission')


def close_owner_recording(output_root, *, owner, scene, recording_path,
        execution_freeze_sha256, reservation_sha256, before_admission=None):
    """Publish data completion only; parent runtime/process seals remain required."""
    owner=_owner(owner);scene=copy.deepcopy(scene)
    p._validate_scene_entry(scene,owner['scene_id'],owner['ordinal']//3,p.COLLECTION_SPLIT)
    for value in (execution_freeze_sha256,reservation_sha256):p._digest(value,'Close binding')
    if before_admission is not None and not callable(before_admission):raise ValueError('Live close guard required')
    output_root=_path(output_root);recording_path=_path(recording_path)
    if recording_path != output_root/'intervals':
        raise ValueError('Owner recording namespace differs from output root')
    summary=_recording(recording_path,scene)
    manifest={'version':1,'kind':'puck-on-policy-owner-recording-close-v1',
        'lineage_sha256':p.PROTOCOL_SHA256,'owner':owner,'scene':scene,
        'recording_path':str(recording_path),'execution_freeze_sha256':execution_freeze_sha256,
        'reservation_sha256':reservation_sha256,'status':'recording_closed',
        **summary,**copy.deepcopy(_AUTHORITY)}
    if len(p._canonical_bytes(manifest,'Owner close'))>MiB:raise ValueError('Owner close exceeds one MiB')
    def guard():
        if before_admission is not None:before_admission()
        _same(summary,_recording(recording_path,scene),'Recording')
        if before_admission is not None:before_admission()
    guard()
    return p._atomic_manifest(_path(output_root),'owner-terminal.json',manifest,before_admission=guard)


def read_closed_owner(path):
    raw=_publication(_path(path),'owner-terminal.json')
    if len(raw)>MiB:raise ValueError('Owner close exceeds one MiB')
    manifest=_json(raw)
    if type(manifest) is not dict or set(manifest)!=_OWNER_FIELDS:
        raise ValueError('Exact owner recording close fields required')
    expected={'version':1,'kind':'puck-on-policy-owner-recording-close-v1',
              'lineage_sha256':p.PROTOCOL_SHA256,'status':'recording_closed',**_AUTHORITY}
    for key,value in expected.items():_same(value,manifest[key],'Owner close '+key)
    owner=_owner(manifest['owner']);scene=manifest['scene']
    p._validate_scene_entry(scene,owner['scene_id'],owner['ordinal']//3,p.COLLECTION_SPLIT)
    for key in ('execution_freeze_sha256','reservation_sha256'):p._digest(manifest[key],key)
    if _path(manifest['recording_path'])!=_path(path).parent/'intervals':
        raise ValueError('Closed owner recording namespace differs')
    summary=_recording(manifest['recording_path'],scene)
    _same(summary,{key:manifest[key] for key in summary},'Closed recording')
    if _publication(path,'owner-terminal.json')!=raw:
        raise ValueError('Owner close changed during read')
    return copy.deepcopy(manifest)


def _owners(roots, execution_sha, reservation_sha):
    if type(roots) not in (list,tuple) or len(roots)!=12:
        raise ValueError('Exactly twelve fixed owner roots required')
    owners=[];coverage={str(seed):0 for seed in (21,22,23)};intervals=0;paths=set();scenes={}
    for ordinal,root in enumerate(roots):
        root=_path(root)
        if root.name!=f'collection-{6110+ordinal//3}-seed-{21+ordinal%3}' or root in paths:
            raise ValueError('Collection owner root roster differs')
        paths.add(root);path=root/'owner-terminal.json';manifest=read_closed_owner(path)
        if manifest['owner']['ordinal']!=ordinal:raise ValueError('Collection owner ordinal reordered')
        if manifest['execution_freeze_sha256']!=execution_sha or manifest['reservation_sha256']!=reservation_sha:
            raise ValueError('Collection owner admission bindings differ')
        scene_id=manifest['owner']['scene_id']
        if scene_id in scenes:_same(scenes[scene_id],manifest['scene'],'Collector scene')
        else:scenes[scene_id]=manifest['scene']
        raw=_publication(path,'owner-terminal.json')
        owners.append({'owner':manifest['owner'],'root':str(root),'sha256':p._sha256(raw),
                       'intervals':manifest['intervals'],'coverage_count':manifest['coverage_count']})
        coverage[str(manifest['owner']['model_seed'])]+=manifest['coverage_count']
        intervals+=manifest['intervals']
    for field in ('canonical_scene_sha256','scientific_initial_sha256','payload_sha256'):
        if len({scene[field] for scene in scenes.values()})!=4:
            raise ValueError('Collection scene identity alias or collision')
    return {'owners':owners,'intervals':intervals,'coverage_by_model':coverage,
            'status':'recordings_complete' if all(coverage.values()) else 'coverage_failed'}


def close_collection_recordings(output_root, *, owner_roots, execution_freeze_sha256,
        reservation_sha256, before_admission=None):
    for value in (execution_freeze_sha256,reservation_sha256):p._digest(value,'Stage close binding')
    if before_admission is not None and not callable(before_admission):raise ValueError('Live close guard required')
    roots=tuple(_path(r) for r in owner_roots) if type(owner_roots) in (list,tuple) else owner_roots
    summary=_owners(roots,execution_freeze_sha256,reservation_sha256)
    manifest={'version':1,'kind':'puck-on-policy-collection-recording-close-v1',
        'lineage_sha256':p.PROTOCOL_SHA256,'execution_freeze_sha256':execution_freeze_sha256,
        'reservation_sha256':reservation_sha256,**summary,**copy.deepcopy(_AUTHORITY)}
    if len(p._canonical_bytes(manifest,'Collection close'))>MiB:raise ValueError('Collection close exceeds one MiB')
    def guard():
        if before_admission is not None:before_admission()
        _same(summary,_owners(roots,execution_freeze_sha256,reservation_sha256),'Collection recordings')
        if before_admission is not None:before_admission()
    guard()
    return p._atomic_manifest(_path(output_root),'collection-terminal.json',manifest,before_admission=guard)


def read_closed_collection(path):
    raw=_publication(_path(path),'collection-terminal.json')
    if len(raw)>MiB:raise ValueError('Collection close exceeds one MiB')
    manifest=_json(raw)
    if type(manifest) is not dict or set(manifest)!=_STAGE_FIELDS:
        raise ValueError('Exact collection recording close fields required')
    for key,value in {'version':1,'kind':'puck-on-policy-collection-recording-close-v1',
            'lineage_sha256':p.PROTOCOL_SHA256,**_AUTHORITY}.items():_same(value,manifest[key],key)
    for key in ('execution_freeze_sha256','reservation_sha256'):p._digest(manifest[key],key)
    owners=manifest['owners']
    if type(owners) is not list or len(owners)!=12:raise ValueError('Exactly twelve owner closes required')
    summary=_owners([row['root'] for row in owners],manifest['execution_freeze_sha256'],manifest['reservation_sha256'])
    _same(summary,{key:manifest[key] for key in summary},'Closed collection')
    if _publication(path,'collection-terminal.json')!=raw:
        raise ValueError('Collection close changed during read')
    return copy.deepcopy(manifest)


def run_collection_episode(execution, env, observation, state, world, contact, probe, writer,
        *, output_root, reservation_sha256, before_admission=None):
    """One admitted caller's natural episode; no runtime or process authority.

    Construction and full parent admission are caller obligations. This reuses
    the held interval path and closes only its actual recording, not the process.
    """
    from .puck_execution import _HeldCollectionExecution
    if not isinstance(execution,_HeldCollectionExecution):
        writer.stop();raise ValueError('Held collection execution required')
    try:
        description=execution.description
        if state.get('tick')!=0 or state.get('reason') is not None or env._t!=0:
            raise ValueError('A single fresh natural collection episode is required')
        _initial(world,state,description['scene'])
        if writer._broken or writer._tick!=0:
            raise ValueError('A fresh unused interval writer is required')
        execution.check_parameters()
        own=learning.initial_cursor();mode=own['mode']
        for _ in range(600):
            completed=execution.native_interval(env,observation,state,world,contact,own,mode,probe,writer)
            observation,state,world,contact,own,mode=(completed[key] for key in
                ('observation','state','world','contact','own','teacher_mode'))
            if state['reason'] is not None:break
        writer.stop()
        if state['reason'] is None:raise ValueError('Collection episode did not terminate at its fixed bound')
        envelope=description['puck_on_policy'];declared=description['owner']
        owner={'ordinal':envelope['ordinal'],**{key:declared[key] for key in ('owner_id','scene_id','model_seed')}}
        def guard():
            execution.check_parameters()
            if before_admission is not None:before_admission()
        result=close_owner_recording(output_root,owner=owner,scene=description['scene'],
            recording_path=writer.path,execution_freeze_sha256=envelope['execution_freeze_sha256'],
            reservation_sha256=reservation_sha256,before_admission=guard)
        return {'recording_close':result,'completed':completed,'native_authorized':False,
                'collection_authorized':False,'executable':False,'qualification_claims':[]}
    except BaseException:
        writer.stop();execution._fail();raise
