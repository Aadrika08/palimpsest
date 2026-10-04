"""Travel development selects completed changed routes, not acquisition alone."""
import copy
import json
import pytest
from pathlib import Path
from scripts import memory_decision_pilot as p, memory_waypoint_study as study
from palimpsest import memory_decision_world as world


def plan(tmp_path):
    repo=Path(p.__file__).resolve().parents[1]
    return {'repo':str(repo),'assets':str(tmp_path/'assets'),'history_root':str(tmp_path/'history'),
            'output':str(tmp_path/'phase'/'development'),'phase_root':str(tmp_path/'phase'),
            'source_identity':{},'protocol_sha256':p.TRAVEL_PROTOCOL_SHA256,'geometry_valid':True}


def success():
    return dict(status='recorded',raw_audit_pass=True,acquired=True,goal=True,
                first_commitment_blocked=True,retreat_completed=True,replans=1)


def test_travel_jobs_bind_full_changed_probe_and_reject_other_protocols(tmp_path):
    spec=p.travel_specs('travel-development')[0]
    job=p.make_job('travel-development',spec,plan(tmp_path),'full')
    assert p.validate_job(job)==job
    assert job['version']==3 and job['case']['kind']=='change'
    assert job['case']['mirrored'] is False
    assert p.owner_allocation('travel-development','full',p.TRAVEL_PROTOCOL_SHA256)==(720,730)
    for key,value in [('version',2),('protocol_sha256',p.WAYPOINT_PROTOCOL_SHA256),('operation','prefix')]:
        bad=copy.deepcopy(job);bad[key]=value
        with pytest.raises(ValueError):p.validate_job(bad)
    with pytest.raises(ValueError):p.owner_allocation('pilot','condition',p.TRAVEL_PROTOCOL_SHA256)


@pytest.mark.parametrize('failure',[
    dict(status='failed',raw_audit_pass=True,retained_task_failure=True,acquired=False,goal=False),
    dict(status='recorded',raw_audit_pass=True,retained_task_failure=True,acquired=True,goal=False),
])
def test_travel_selection_advances_audited_failures_before_or_after_acquisition(tmp_path,monkeypatch,failure):
    outcomes=[failure,success()]
    def launch(stage,spec,plan,storage,deadline,**kw):
        assert stage=='travel-development' and spec['operation']=='full'
        return outcomes.pop(0)
    monkeypatch.setattr(p,'launch_owner',launch)
    result=study.run_development(plan(tmp_path),None,None)
    assert [r['goal'] for r in result['attempted']]==[False,True]
    assert result['selected_profile_sha256']==world.TRAVEL_PROFILE_HASHES[1]
    assert result['unattempted']==['candidate-d15']


@pytest.mark.parametrize('bad',[
    dict(status='recorded',raw_audit_pass=True,acquired=True,goal=False),
    dict(status='recorded',raw_audit_pass=False,retained_task_failure=True,acquired=True,goal=False),
    dict(status='recorded',raw_audit_pass=True,acquired=True,goal=True,retreat_completed=False,replans=0),
])
def test_partial_or_unproved_travel_result_stops_without_selection(tmp_path,monkeypatch,bad):
    monkeypatch.setattr(p,'launch_owner',lambda *a,**kw:bad)
    result=study.run_development(plan(tmp_path),None,None)
    assert len(result['attempted'])==1
    assert result['selected_profile_sha256'] is None
    assert result['unattempted']==['candidate-d20','candidate-d15']


def test_full_task_failure_requires_actual_terminal_packet_event_and_no_later_policy():
    message='selected_waypoint_unavailable: exit'
    outcome={'reason':'runtime_failure','type':'CueUnavailable','message':message,'steps':10}
    report={'goal':False,'total_ticks':10,'final_phase':'failed','outcome':outcome,
            'final_memory':{'supervisor':{'phase':'follow_route','continuation_start_tick':5}}}
    data={'events':[{'kind':'memory_sensed','episode_step':10,'packet':{'tick':10}},
                    {'kind':'runtime_failure','episode_step':10,'error':outcome}]}
    assert p.audit_travel_task_failure(data,report)=='CueUnavailable'
    for events in [data['events'][1:],data['events'][:1],data['events']+[{'kind':'neural_policy_call','episode_step':10}]]:
        with pytest.raises(ValueError):p.audit_travel_task_failure({'events':events},report)
    bad=copy.deepcopy(report);bad['outcome']['type']='RuntimeError'
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,bad)


def test_post_acquisition_time_limit_uses_declared_continuation_boundary():
    total=1627;outcome={'reason':'time_limit','episode':0,'steps':total}
    rows=[{'pose':[0.,0.,0.],'next_pose':[.01,0.,0.],'action':[.5,0.]} for _ in range(total)]
    data={'rows':rows,'events':[{'kind':'episode_finished','outcome':outcome}]}
    report={'goal':False,'outcome':outcome,'total_ticks':total,'final_phase':'truncated',
            'final_memory':{'supervisor':{'continuation_start_tick':727}}}
    assert p.audit_travel_task_failure(data,report)=='time_limit'
    bad=copy.deepcopy(report);bad['final_memory']['supervisor']['continuation_start_tick']=728
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,bad)


def test_actual_travel_cli_preserves_immutable_candidates_and_stops_at_qualification_failure(tmp_path,monkeypatch):
    identity={'synthetic-software-fixture':True};repo=Path(p.__file__).resolve().parents[1]
    def preflight(repo,assets,history,output,phase,deadline):
        return {'repo':str(repo),'assets':str(assets),'history_root':str(history),'output':str(output),
                'phase_root':str(phase),'source_identity':identity,'geometry_valid':True}
    monkeypatch.setattr(p,'preflight',preflight);monkeypatch.setattr(p,'source_identity',lambda *a:identity)
    def launch(stage,spec,plan,storage,deadline,**kw):
        if stage=='travel-development':return success()
        assert stage=='travel-feasibility' and spec['id']=='south-no-event'
        return dict(status='recorded',acquired=True,goal=False,raw_audit_pass=True)
    monkeypatch.setattr(p,'launch_owner',launch)
    out=tmp_path/'output'
    assert study.main(['--amendment','travel-handoff','--repo',str(repo),'--assets',str(tmp_path/'assets'),
        '--history-root',str(tmp_path/'history'),'--output',str(out)])==0
    r=json.loads((out/'execution.json').read_text());c=json.loads((out/'candidates.json').read_text())
    assert r['stage_caps']=={'development':2300,'prerequisites':4300,'readout':600}
    assert len(c['candidates'])==3 and r['stages']['development']['unattempted']==['candidate-d20','candidate-d15']
    assert len(r['stages']['prerequisites']['attempted'])==1
    assert len(r['stages']['prerequisites']['unattempted'])==7
    assert r['stages']['prerequisites']['status']=='failed' and r['paired_pilot']=='unattempted-by-scope'
    assert r['source_identity_unchanged'] and not list(out.rglob('*.pending'))
    assert (out/'selected-profile.json').exists()


@pytest.mark.parametrize('failure,expected',[
    ('cue',True),('cue-missing-runtime',False),('supervisor',True),('supervisor-unknown-error',False),
])
def test_owner_dispatch_requires_real_pre_acquisition_terminal_proof(tmp_path,monkeypatch,failure,expected):
    """Only the native process is doubled; real writer/reader/bindings/replay run."""
    import numpy as np
    from palimpsest import memory_decision as md
    from palimpsest.records import RunWriter
    from palimpsest.snapshots import state_digest
    from palimpsest.profiles import validate_decision
    from palimpsest import evaluate
    current=plan(tmp_path);current['source_identity']={'source_sha256':{},'lock_sha256':'0'*64,'upstream_commit':'0'*40}
    storage=p.phase_budget(Path(current['phase_root']));Path(current['output']).mkdir(parents=True)
    def native_process(command,output,timeout,environment,**kwargs):
        job=json.loads(command[-1]);case=job['case'];run=Path(job['output'])
        profile=validate_decision(world.SCENARIO,'checker','flynn',profile_sha256=case['profile_sha256'])
        writer=RunWriter(run/'recording',{'status':'running','controller':'flynn','requested_device':'cpu',
            'run_id':job['run_id'],'scenario':profile,'memory_case':case,'memory_decision_pilot_job':job,
            'memory_decision_pilot_protocol_sha256':job['protocol_sha256'],'recording_max_bytes':512*p.MiB},max_bytes=512*p.MiB)
        writer.event('environment',**job['source_identity']);state=md.initialize(case)
        total=300 if failure.startswith('supervisor') else 1
        row={'pose':np.array([-2.5,0.,0.]),'next_pose':np.array([-2.5,0.,0.]),
             'action':np.zeros(2,np.float32),'raw_output':np.zeros(2,np.float32),
             'encoded_input':np.zeros(4813,np.float32),'cam_left':np.zeros((128,128,3),np.uint8),
             'cam_right':np.zeros((128,128,3),np.uint8),'sensors':np.array([0.,0.,1.,0.],np.float32)}
        for tick in range(total+1):
            pose=[-2.5,0.,np.pi if tick==total and failure.startswith('cue') else 0.]
            packet=md.capture_symbolic(*world.reconstruct_inputs(case,pose,tick,gate_result='not_requested'),episode_id='episode-0',tick=tick)
            writer.event('memory_sensed',episode_step=tick,packet=packet)
            try:state,bearing,details=md.advance_memory(state,packet)
            except md.CueUnavailable as error:
                message=str(error);break
            for detail in details:writer.event('memory_decision',episode_step=tick,detail=detail)
            if tick==total:
                message='Memory-v2 supervisor failure: waypoint_timeout';break
            writer.event('memory_cue',episode_step=tick,bearing=bearing)
            sensors={'collision':False,'collision_angle':None,'wind_direction':bearing}
            row['sensors']=np.array([0.,0.,*bearing],np.float32)
            if tick==total-1 and failure.startswith('cue'):row['next_pose']=np.array([-2.5,0.,np.pi])
            writer.event('neural_policy_call',episode=0,episode_step=tick,tick=tick,sensors=sensors,
                result_sha256={k:state_digest(row[k]) for k in ('action','encoded_input','raw_output')},
                cameras_sha256={k:state_digest(row[k]) for k in ('cam_left','cam_right')},
                observation_sha256=state_digest({'cam_left':row['cam_left'],'cam_right':row['cam_right'],'sensors':sensors}))
            writer.tick(0,tick,**row)
        outcome={'reason':'runtime_failure','type':'CueUnavailable' if failure.startswith('cue') else 'ValueError',
                 'message':message,'steps':total}
        if failure=='supervisor-unknown-error':outcome.update(type='OSError',message='unknown renderer error')
        writer.event('fixture_removed_runtime' if failure=='cue-missing-runtime' else 'runtime_failure',episode_step=total,error=outcome)
        writer.finish({},status='failed')
        world_state=world.initial_state(case);world_state['last_tick']=total
        report={'status':'failed','acquired':False,'goal':False,'continuation_ticks':0,'total_ticks':total,
            'error':{'message':'Real CPU FLYNN prefix did not obtain both open observations and return'},
            'final_phase':'failed','outcome':outcome,'world_state':world_state,'final_memory':state}
        p.write_control(run/'worker-report.json',report,storage)
        return {'status':'failed','returncode':1,'timeout_seconds':timeout,'output':str(output)}
    monkeypatch.setattr(evaluate,'bounded_process',native_process)
    result=p.launch_owner('travel-development',p.travel_specs('travel-development')[0],current,storage,p.time.monotonic()+1000)
    assert (result.get('retained_task_failure') is True)==expected, result.get('audit_error')
    assert (result.get('raw_audit_pass') is True)==expected


@pytest.mark.parametrize('failure_stage',['development','preparation','after-report'])
def test_exceptional_phase_exit_retains_qualification_disposition(tmp_path,monkeypatch,failure_stage):
    identity={'synthetic-software-fixture':True};repo=Path(p.__file__).resolve().parents[1]
    def preflight(repo,assets,history,output,phase,deadline):
        return {'repo':str(repo),'assets':str(assets),'history_root':str(history),'output':str(output),
                'phase_root':str(phase),'source_identity':identity,'geometry_valid':True}
    monkeypatch.setattr(p,'preflight',preflight);monkeypatch.setattr(p,'source_identity',lambda *a:identity)
    monkeypatch.setattr(p,'launch_owner',lambda *a,**kw:success())
    def stop(*a,**kw):raise TimeoutError('software fixture stage deadline')
    if failure_stage=='development':monkeypatch.setattr(study,'run_development',stop)
    else:
        def qualification(plan,selected,storage,deadline):
            if failure_stage=='after-report':
                (Path(plan['phase_root'])/'prerequisites').mkdir()
                p.write_control(Path(plan['phase_root'])/'prerequisites/report.json',
                    {'status':'failed','attempted':[{'job_id':'south-no-event'}],'unattempted':['south-change','north-no-event','north-change','south-prefix','north-prefix','restore-1','restore-2']},storage)
            stop()
        monkeypatch.setattr(study,'run_prerequisites',qualification)
    out=tmp_path/'phase-exception'
    assert study.main(['--amendment','travel-handoff','--repo',str(repo),'--assets',str(tmp_path/'assets'),
        '--history-root',str(tmp_path/'history'),'--output',str(out)])==1
    receipt=json.loads((out/'execution.json').read_text());stage=receipt['stages']['prerequisites']
    assert receipt['status']=='execution-failed'
    if failure_stage=='after-report':assert len(stage['attempted'])==1 and len(stage['unattempted'])==7
    else:assert stage['status']=='unattempted' and len(stage['unattempted'])==8
