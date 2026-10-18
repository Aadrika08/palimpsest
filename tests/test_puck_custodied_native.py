"""Actual authored CPU model, faithful native fixtures and real disk transactions."""
from pathlib import Path
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize('scenario',[
    'success','two-intervals','parameter-before','parameter-during-step',
    'file-during-step','wrong-goal','stale-native-tick','publication-failure',
    'file-after-publication','unmaterialized','closed','mixed-model','second-file-drift'])
def test_custodied_native_interval_on_authored_inputs(tmp_path,scenario):
    # Each child isolates the actual Torch profile and the faithful fake native
    # runtime. It opens only temporary authored bundle/source files.
    code=r'''
from pathlib import Path
import sys
import numpy as np
import torch
from unittest.mock import patch
from types import SimpleNamespace
from test_puck_execution import context
from test_puck_on_policy_native_interval import NativeIntervalTests
from test_puck_profile import OWNERSHIP,raw_contacts
from palimpsest import puck_on_policy as adapter,puck_profile as puck,puck_model
from palimpsest.body_profile import effective_control
from palimpsest.records import RunWriter

fixture=NativeIntervalTests(methodName='runTest');fixture.setUp()
from scripts import verify_puck_mechanics as native_gate
world_patch=patch.object(native_gate,'world_from',side_effect=lambda env,goal:{**fixture.world,'time_s':env.data.time})
world_patch.start();fixture.addCleanup(world_patch.stop)
execution,custody=context(Path(sys.argv[1]))
scenario=sys.argv[2]
assert callable(getattr(execution,'native_interval',None)), 'Custodied native interval API missing'
execution.__enter__()
model=None if scenario=='unmaterialized' else execution.materialize_original_model()
fixture.world.update(rover_pose=[-1.05,-.5,0.],puck_xyz=[-.5,-.5,.062],
                     goal_xy=execution.description['scene']['layout']['goal_xy'])
world=dict(fixture.world)
state=puck.initialize(world,'fixture')
contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
writer=adapter.PuckIntervalWriter(fixture.path,max_bytes=2*1024**2)
calls={'teacher':0,'predict':0,'step':0}
from palimpsest import puck_teacher
teacher=puck_teacher.decide;predict=puck_model.predict

def query(*args):calls['teacher']+=1;return teacher(*args)
def inference(*args):calls['predict']+=1;return predict(*args)

def drift_file():
    path=Path(custody['roles']['bundle']['root'])/'report.json'
    path.write_bytes(path.read_bytes()+b'changed')

def step(action):
    calls['step']+=1
    fixture.env._t+=1;fixture.env.data.time=fixture.env._t*.02
    fixture.env.data.ctrl[:]=effective_control(action)
    if scenario=='parameter-during-step':
        with torch.no_grad():model[0].bias[0]+=1
    if scenario=='file-during-step' or scenario=='second-file-drift' and calls['step']==2:drift_file()
    if scenario=='stale-native-tick':fixture.env._t-=1
    return fixture.observation,0.,False,False,{'dist_to_goal':1.,'stalled':False}
fixture.env.step=step
probe=SimpleNamespace(ownership=OWNERSHIP,install=lambda:None,begin=lambda t:None,
    end=lambda:raw_contacts(fixture.env._t),close=lambda:None)
if scenario=='parameter-before':
    with torch.no_grad():model[0].bias[0]+=1
if scenario=='wrong-goal':world['goal_xy']=[99.,99.]
if scenario=='closed':execution.__exit__(None,None,None)
if scenario=='file-after-publication':
    original=writer.publish
    def publish(*args,**kwargs):
        result=original(*args,**kwargs);drift_file();return result
    writer.publish=publish
own=fixture.own;mode=fixture.mode
failure=None
try:
    with patch.object(puck_teacher,'decide',side_effect=query),patch.object(puck_model,'predict',side_effect=inference):
        if scenario=='mixed-model':
            from scripts.verify_puck_mechanics import on_policy_interval
            on_policy_interval(fixture.env,fixture.observation,state,world,contact,own,mode,
                model,probe,writer,execution=execution)
        else:
            with patch.object(RunWriter,'finish',side_effect=OSError('authored publication failure')) if scenario=='publication-failure' else __import__('contextlib').nullcontext():
                completed=execution.native_interval(fixture.env,fixture.observation,state,world,contact,
                    own,mode,probe,writer)
                if scenario in ('two-intervals','second-file-drift'):
                    completed=execution.native_interval(fixture.env,completed['observation'],completed['state'],
                        completed['world'],completed['contact'],completed['own'],completed['teacher_mode'],probe,writer)
except (ValueError,RuntimeError,OSError) as error:failure=error
rows=list(adapter.read_committed_intervals(fixture.path))
if scenario in ('success','two-intervals'):
    assert failure is None,failure
    n=2 if scenario=='two-intervals' else 1
    assert calls=={'teacher':n,'predict':n,'step':n},calls
    assert len(rows)==n and completed['own']['tick']==n and fixture.own['tick']==0
    assert completed['teacher_mode']==completed['own']['mode']
    for row in rows:
        assert row['row']['action'].tobytes()==row['row']['predicted_action'].tobytes()
    execution.check_parameters();execution.__exit__(None,None,None)
else:
    assert failure is not None,'Custody/native/publication failure accepted'
    assert writer._broken,'Failed native route left writer reusable'
    assert len(rows)==(1 if scenario in ('file-after-publication','second-file-drift') else 0),len(rows)
    assert fixture.own['tick']==0
    n=0 if scenario in ('parameter-before','wrong-goal','unmaterialized','closed','mixed-model') else 2 if scenario=='second-file-drift' else 1
    assert calls=={'teacher':n,'predict':n,'step':n},calls
    try:execution.recheck()
    except RuntimeError:pass
    else:raise AssertionError('Failed native route left custody usable')
    try:execution.__exit__(RuntimeError,RuntimeError('authored cleanup'),None)
    except (ValueError,RuntimeError,OSError):pass
fixture.doCleanups()
print('authored native custody scenario passed')
'''
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src:.:tests',
         'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path/'inputs'),scenario],
                          cwd=Path(__file__).resolve().parents[1],env=env,
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_native_pipeline_imports_from_declared_package_path_without_fixture_path_changes():
    code='from scripts.verify_puck_mechanics import on_policy_interval; assert callable(on_policy_interval)'
    result=subprocess.run([sys.executable,'-c',code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src:.'},
        capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
