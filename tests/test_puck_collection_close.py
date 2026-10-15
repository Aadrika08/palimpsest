"""Real disk close/reduction on authored rows; no original model or study."""
import importlib
import importlib.util
from pathlib import Path
import pytest
import test_puck_on_policy_native_interval as native_fixtures
from palimpsest import puck_on_policy as p


def api():
    name='palimpsest.puck_collection_close'
    assert importlib.util.find_spec(name), 'Durable collection close API missing'
    return importlib.import_module(name)


def test_no_durable_owner_close_for_unfinished_prefix(tmp_path):
    module=api()
    path,scene,event=recording(tmp_path,terminal=False)
    with pytest.raises(ValueError,match='terminal'):
        module.close_owner_recording(tmp_path,owner=owner(0),scene=scene,
            recording_path=path,execution_freeze_sha256='a'*64,reservation_sha256='b'*64)
    assert not p._publication_paths(tmp_path,'owner-terminal.json')['admission'].exists()


def owner(ordinal):
    scene,seed=6110+ordinal//3,21+ordinal%3
    return {'ordinal':ordinal,'owner_id':f'collection-{scene}-seed-{seed}',
            'scene_id':scene,'model_seed':seed}


def scene_entry(slot):
    layout=p._row(6110+slot,slot)
    layout['split']=p.COLLECTION_SPLIT
    return {'scene_id':6110+slot,'slot':slot,'split':p.COLLECTION_SPLIT,
            **p.scene_candidate_identities(layout),'layout':layout}


@pytest.mark.parametrize('ordinal',[-1,True,12])
def test_invalid_fixed_owner_roster_refuses_before_data(tmp_path,ordinal):
    module=api()
    with pytest.raises(ValueError,match='ordinal'):
        module.close_owner_recording(tmp_path,owner={'ordinal':ordinal},scene=scene_entry(0),
            recording_path=tmp_path/'absent',execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_natural_episode_entry_exists_without_changing_historical_denial():
    module=api()
    assert callable(module.run_collection_episode)
    from scripts.verify_puck_mechanics import owner as historical
    with pytest.raises(ValueError,match='not qualified'):historical({'puck_on_policy':{}})


def recording(tmp_path,ordinal=0,*,covered=False,terminal=True,contact_enabled=None):
    import numpy as np
    from palimpsest import puck_profile as puck,snapshots
    from test_puck_profile import OWNERSHIP,raw_contacts
    fixture=native_fixtures.NativeIntervalTests(methodName='runTest');fixture.setUp()
    try:
        scene=scene_entry(ordinal//3);layout=scene['layout']
        if covered:
            offset=(ordinal//3)*.5
            layout.update(rover_pose=[-.62+offset,-.055,0.],puck_xy=[offset,0.],goal_xy=[1.+offset,0.])
            scene.update(p.scene_candidate_identities(layout))
        fixture.world.update(rover_pose=layout['rover_pose'],puck_xyz=[*layout['puck_xy'],.062],
                             goal_xy=layout['goal_xy'])
        contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
        contact_enabled=covered if contact_enabled is None else contact_enabled
        if contact_enabled:contact['rover_puck_contact']=True
        fixture.sensors=puck.project(fixture.world,contact)
        staged=fixture.staged();arrays,event=fixture.payload(staged)
        if contact_enabled:
            event['contact_before']['rover_puck_contact']=True
            event['contact']['rover_puck_contact']=True
        if terminal:event['world']['puck_xyz']=[*layout['puck_xy'],.15]
        state,reward=puck.advance(event['state_before'],event['world'],event['contact'],fixture.prediction.tolist())
        event.update(state=state,reward=reward)
        arrays['world_after']=np.array([event['world']['time_s'],*event['world']['rover_pose'],
            *event['world']['puck_xyz'],*event['world']['puck_velocity_xy'],*event['world']['goal_xy']],np.float64)
        arrays['reward']=np.asarray(reward,np.float64)
        own={**staged['own_pending']['after'],'tick':1}
        task={'state':state,'world':event['world'],'contact':event['contact'],'own_supervisor_cursor':own}
        arrays['task_sha256']=np.frombuffer(bytes.fromhex(snapshots.state_digest(task)),np.uint8)
        path=tmp_path/'intervals';writer=p.PuckIntervalWriter(path,max_bytes=2*1024**2)
        writer.publish(staged,arrays,event,completed_tick=1);writer.stop()
        return path,scene,event
    finally:fixture.doCleanups()


def close(tmp_path,ordinal=0,guard=None,*,covered=False,contact_enabled=None):
    module=api();path,scene,event=recording(tmp_path,ordinal,covered=covered,contact_enabled=contact_enabled)
    result=module.close_owner_recording(tmp_path,owner=owner(ordinal),scene=scene,
        recording_path=path,execution_freeze_sha256='a'*64,reservation_sha256='b'*64,
        before_admission=guard)
    return result,path,event


def test_natural_nongoal_recording_closes_without_any_execution_grant(tmp_path):
    module=api();result,path,event=close(tmp_path)
    receipt=module.read_closed_owner(Path(result['manifest_path']))
    assert receipt['status']=='recording_closed' and receipt['intervals']==1
    assert receipt['terminal_reason']=='puck_height'
    assert receipt['coverage_count']==0 and len(receipt['commitments'])==1
    assert receipt['native_authorized'] is receipt['collection_authorized'] is receipt['fitting_authorized'] is False
    assert receipt['qualification_claims']==[]
    with pytest.raises((ValueError,FileExistsError)):
        module.close_owner_recording(tmp_path,owner=owner(0),scene=scene_entry(0),
            recording_path=path,execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_final_guard_failure_never_admits_a_terminal(tmp_path):
    module=api()
    def fail():raise RuntimeError('held inputs changed')
    with pytest.raises(RuntimeError,match='held inputs changed'):close(tmp_path,guard=fail)
    assert not p._publication_paths(tmp_path,'owner-terminal.json')['admission'].exists()
    with pytest.raises(ValueError):module.read_closed_owner(tmp_path/'owner-terminal.json')


def test_uncommitted_tail_cannot_be_reported_as_complete(tmp_path):
    module=api();path,scene,event=recording(tmp_path)
    (path/'000002').mkdir()
    with pytest.raises(ValueError,match='pending|prefix|uncommitted|namespace'):
        module.close_owner_recording(tmp_path,owner=owner(0),scene=scene,recording_path=path,
            execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_closed_owner_rereads_actual_committed_rows(tmp_path):
    module=api();result,path,event=close(tmp_path)
    manifest=path/'000001/recording/manifest.json'
    manifest.write_bytes(manifest.read_bytes()+b' ')
    with pytest.raises(ValueError):module.read_closed_owner(Path(result['manifest_path']))


def test_twelve_natural_nongoals_publish_coverage_failure_without_training(tmp_path):
    module=api();roots=[]
    for ordinal in range(12):
        root=tmp_path/owner(ordinal)['owner_id'];root.mkdir()
        close(root,ordinal);roots.append(root)
    output=tmp_path/'stage';output.mkdir()
    result=module.close_collection_recordings(output,owner_roots=roots,
        execution_freeze_sha256='a'*64,reservation_sha256='b'*64)
    receipt=module.read_closed_collection(Path(result['manifest_path']))
    assert receipt['status']=='coverage_failed'
    assert receipt['intervals']==12
    assert receipt['coverage_by_model']=={'21':0,'22':0,'23':0}
    assert receipt['fitting_authorized'] is receipt['collection_authorized'] is False
    assert len(receipt['owners'])==12


def test_partial_or_reordered_roster_is_not_collection_close(tmp_path):
    module=api();result,path,event=close(tmp_path)
    with pytest.raises(ValueError,match='twelve|roster'):
        module.close_collection_recordings(tmp_path,owner_roots=[tmp_path],
            execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


@pytest.mark.parametrize('scenario',['normal','wrong-initial'])
def test_actual_authored_model_native_episode_to_durable_close(tmp_path,scenario):
    import os,subprocess,sys
    code=r'''
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import numpy as np
from test_puck_execution import context
import test_puck_on_policy_native_interval as fixtures
from test_puck_profile import OWNERSHIP,raw_contacts
from palimpsest import puck_collection_close as close,puck_on_policy as adapter,puck_profile as puck
from palimpsest.body_profile import effective_control
from scripts import verify_puck_mechanics as gate
fixture=fixtures.NativeIntervalTests(methodName='runTest');fixture.setUp()
world_patch=patch.object(gate,'world_from',side_effect=lambda env,goal:{**fixture.world,'time_s':env.data.time})
world_patch.start();fixture.addCleanup(world_patch.stop)
execution,custody=context(Path(sys.argv[1])/'inputs')
writer=adapter.PuckIntervalWriter(fixture.path,max_bytes=2*1024**2)
execution.__enter__();execution.materialize_original_model()
scene=execution.description['scene'];layout=scene['layout']
fixture.world.update(rover_pose=list(layout['rover_pose']),puck_xyz=[*layout['puck_xy'],.062],goal_xy=layout['goal_xy'])
if sys.argv[2]=='wrong-initial':fixture.world['rover_pose'][0]+=.1
world=dict(fixture.world);state=puck.initialize(world,'fixture')
contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
calls=[]
def step(action):
    calls.append(action)
    fixture.env._t+=1;fixture.env.data.time=.02;fixture.env.data.ctrl[:]=effective_control(action)
    fixture.world['puck_xyz']=[*layout['puck_xy'],.15]
    return fixture.observation,0.,False,False,{'dist_to_goal':1.,'stalled':False}
fixture.env.step=step
probe=SimpleNamespace(ownership=OWNERSHIP,install=lambda:None,begin=lambda t:None,end=lambda:raw_contacts(fixture.env._t),close=lambda:None)
try:
    result=close.run_collection_episode(execution,fixture.env,fixture.observation,state,world,contact,probe,writer,
        output_root=fixture.path.parent,reservation_sha256='b'*64)
except ValueError as error:
    assert sys.argv[2]=='wrong-initial',error
    assert not calls, 'Wrong scientific initial reached native action'
    assert writer._broken
else:
    assert sys.argv[2]=='normal'
    receipt=close.read_closed_owner(Path(result['recording_close']['manifest_path']))
    assert receipt['intervals']==len(calls)==1 and receipt['terminal_reason']=='puck_height'
    assert result['native_authorized'] is False
    assert writer._broken
    execution.__exit__(None,None,None)
fixture.doCleanups()
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path),scenario],
        cwd=Path(__file__).absolute().parents[1],capture_output=True,text=True,timeout=30,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src:.:tests',
             'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
    assert result.returncode==0,result.stdout+result.stderr



def test_each_collector_model_must_have_motivating_rows_and_all_rows_are_retained(tmp_path):
    module=api();roots=[]
    for ordinal in range(12):
        root=tmp_path/owner(ordinal)['owner_id'];root.mkdir()
        close(root,ordinal,covered=True);roots.append(root)
    output=tmp_path/'stage';output.mkdir()
    result=module.close_collection_recordings(output,owner_roots=roots,
        execution_freeze_sha256='a'*64,reservation_sha256='b'*64)
    receipt=module.read_closed_collection(Path(result['manifest_path']))
    assert receipt['status']=='recordings_complete' and receipt['intervals']==12
    assert receipt['coverage_by_model']=={'21':4,'22':4,'23':4}
    assert receipt['fitting_authorized'] is False


def test_owner_recording_cannot_alias_another_owner_namespace(tmp_path):
    module=api();path,scene,event=recording(tmp_path)
    output=tmp_path/'different';output.mkdir()
    with pytest.raises(ValueError,match='namespace'):
        module.close_owner_recording(output,owner=owner(0),scene=scene,recording_path=path,
            execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_same_scene_cannot_change_between_collectors(tmp_path):
    module=api();roots=[]
    for ordinal in range(12):
        root=tmp_path/owner(ordinal)['owner_id'];root.mkdir()
        close(root,ordinal,covered=ordinal==1);roots.append(root)
    output=tmp_path/'stage';output.mkdir()
    with pytest.raises(ValueError,match='scene'):
        module.close_collection_recordings(output,owner_roots=roots,
            execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_terminal_reader_bounds_bytes_before_copying_manifest(tmp_path,monkeypatch):
    module=api();result,path,event=close(tmp_path)
    original=p._read_exact_file;limits=[]
    def read(root,path,maximum,label,**kwargs):
        if Path(path).name=='owner-terminal.json':limits.append(maximum)
        return original(root,path,maximum,label,**kwargs)
    monkeypatch.setattr(p,'_read_exact_file',read)
    module.read_closed_owner(Path(result['manifest_path']))
    assert limits and max(limits)<=1024**2


def test_collection_scene_identity_aliases_are_not_a_new_scene_roster(tmp_path,monkeypatch):
    import sys
    module=api();original=scene_entry
    def duplicate(slot):
        scene=original(slot);layout=scene['layout']
        zero=original(0)['layout']
        layout.update({key:zero[key] for key in ('rover_pose','puck_xy','goal_xy')})
        scene.update(p.scene_candidate_identities(layout))
        return scene
    monkeypatch.setattr(sys.modules[__name__],'scene_entry',duplicate)
    roots=[]
    for ordinal in range(12):
        root=tmp_path/owner(ordinal)['owner_id'];root.mkdir()
        close(root,ordinal);roots.append(root)
    output=tmp_path/'stage';output.mkdir()
    with pytest.raises(ValueError,match='scene.*alias|scene.*collision'):
        module.close_collection_recordings(output,owner_roots=roots,
            execution_freeze_sha256='a'*64,reservation_sha256='b'*64)



def test_two_locally_valid_rows_cannot_reset_world_between_intervals(tmp_path):
    from test_puck_profile import OWNERSHIP,raw_contacts
    from palimpsest import puck_profile as puck
    module=api();fixture=native_fixtures.NativeIntervalTests(methodName='runTest');fixture.setUp()
    try:
        scene=scene_entry(0);layout=scene['layout']
        fixture.world.update(rover_pose=list(layout['rover_pose']),puck_xyz=[*layout['puck_xy'],.062],
                             goal_xy=layout['goal_xy'])
        fixture.sensors=puck.project(fixture.world,puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.))
        path=tmp_path/'intervals';writer=p.PuckIntervalWriter(path,max_bytes=2*1024**2)
        fixture.publish(writer)
        fixture.world['rover_pose'][0]+=.01
        fixture.sensors=puck.project(fixture.world,puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.))
        fixture.publish(writer,1);writer.stop()
        assert len(list(p.read_committed_intervals(path)))==2
        with pytest.raises(ValueError,match='continuity'):
            module.close_owner_recording(tmp_path,owner=owner(0),scene=scene,recording_path=path,
                execution_freeze_sha256='a'*64,reservation_sha256='b'*64)
    finally:fixture.doCleanups()


def test_one_uncovered_model_fails_without_dropping_its_complete_owners(tmp_path):
    module=api();roots=[]
    for ordinal in range(12):
        root=tmp_path/owner(ordinal)['owner_id'];root.mkdir()
        close(root,ordinal,covered=True,contact_enabled=ordinal%3!=2);roots.append(root)
    output=tmp_path/'stage';output.mkdir()
    result=module.close_collection_recordings(output,owner_roots=roots,
        execution_freeze_sha256='a'*64,reservation_sha256='b'*64)
    receipt=module.read_closed_collection(Path(result['manifest_path']))
    assert receipt['status']=='coverage_failed' and receipt['intervals']==12
    assert receipt['coverage_by_model']=={'21':4,'22':4,'23':0}
    assert len(receipt['owners'])==12 and receipt['fitting_authorized'] is False
