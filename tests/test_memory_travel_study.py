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
