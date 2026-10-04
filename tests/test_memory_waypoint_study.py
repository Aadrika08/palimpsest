"""Bounded amendment selection must not promote infrastructure failures."""
import copy
import importlib
import pytest
from palimpsest import memory_decision_world as world


def study():
    return importlib.import_module('scripts.memory_waypoint_study')


def test_development_advances_only_on_audited_task_failure_and_stops_at_first_success(monkeypatch):
    module = study()
    outcomes = [dict(status='failed',raw_audit_pass=True,retained_task_failure=True,acquired=False),
                dict(status='recorded',raw_audit_pass=True,acquired=True)]
    calls = []
    def launch(stage,spec,plan,storage,deadline,**kwargs):
        calls.append(spec['profile_sha256'])
        return outcomes[len(calls)-1]
    monkeypatch.setattr(module.pilot,'launch_owner',launch)
    result = module.run_development({'geometry_valid':True},None,None)
    assert calls == list(world.WAYPOINT_PROFILE_HASHES[:2])
    assert result['selected_profile_sha256'] == world.WAYPOINT_PROFILE_HASHES[1]
    assert result['unattempted'] == ['candidate-r12']
    assert result['status'] == 'passed'


@pytest.mark.parametrize('outcome',[
    dict(status='failed',raw_audit_pass=False,retained_task_failure=True,acquired=False),
    dict(status='failed',raw_audit_pass=True,retained_task_failure=False,acquired=False),
    dict(status='recorded',raw_audit_pass=True,acquired=False),
])
def test_infrastructure_or_incomplete_acquisition_never_selects_or_advances(monkeypatch,outcome):
    module = study()
    monkeypatch.setattr(module.pilot,'launch_owner',lambda *args,**kwargs:outcome)
    result = module.run_development({'geometry_valid':True},None,None)
    assert len(result['attempted']) == 1
    assert result['selected_profile_sha256'] is None
    assert result['unattempted'] == ['candidate-r13','candidate-r12']
    assert result['status'] == 'failed'


def test_candidate_exhaustion_does_not_wrap_or_retry(monkeypatch):
    module = study()
    monkeypatch.setattr(module.pilot,'launch_owner',lambda *args,**kwargs:dict(
        status='failed',raw_audit_pass=True,retained_task_failure=True,acquired=False))
    result = module.run_development({'geometry_valid':True},None,None)
    assert len(result['attempted']) == 3
    assert result['selected_profile_sha256'] is None
    assert result['unattempted'] == []
    assert result['status'] == 'failed'


def test_amendment_allocations_are_explicit_and_do_not_change_legacy_deadlines():
    module = study()
    p = module.pilot
    assert p.owner_allocation('feasibility','prefix',p.PROTOCOL_SHA256) == (150,160)
    assert p.owner_allocation('waypoint-development','prefix',p.WAYPOINT_PROTOCOL_SHA256) == (360,370)
    assert p.owner_allocation('waypoint-feasibility','full',p.WAYPOINT_PROTOCOL_SHA256) == (720,730)
    assert p.owner_allocation('waypoint-feasibility','repeat',p.WAYPOINT_PROTOCOL_SHA256) == (150,160)
    with pytest.raises(ValueError):
        p.owner_allocation('pilot','condition',p.WAYPOINT_PROTOCOL_SHA256)


def test_job_cannot_change_selected_geometry_or_cross_protocol_boundary(tmp_path):
    module = study()
    p = module.pilot
    plan = {'repo':str(__import__('pathlib').Path(p.__file__).resolve().parents[1]),
            'assets':str(tmp_path/'assets'),'history_root':str(tmp_path/'history'),
            'output':str(tmp_path/'phase'/'development'),'phase_root':str(tmp_path/'phase'),
            'source_identity':{},'protocol_sha256':p.WAYPOINT_PROTOCOL_SHA256}
    spec = module.candidate_specs()[0]
    job = p.make_job('waypoint-development',spec,plan,'prefix')
    assert p.validate_job(job) == job
    assert job['case']['profile_sha256'] == world.WAYPOINT_PROFILE_HASHES[0]
    bad = copy.deepcopy(job)
    bad['case']['profile_sha256'] = world.WAYPOINT_PROFILE_HASHES[1]
    with pytest.raises(ValueError):
        p.validate_job(bad)

    bad = copy.deepcopy(job)
    bad['protocol_sha256'] = p.PROTOCOL_SHA256
    with pytest.raises(ValueError):
        p.validate_job(bad)


def test_nonzero_task_exit_can_be_audited_but_log_or_timeout_failures_cannot(tmp_path):
    import sys
    from palimpsest.evaluate import bounded_process
    from palimpsest.profiles import validate_decision
    p = study().pilot
    supervised = bounded_process([sys.executable,'-c','raise SystemExit(1)'],tmp_path/'owner',5)
    assert supervised['status'] == 'failed' and supervised['returncode'] == 1
    case = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    job = {'operation':'prefix','snapshot_path':None,'case':case,'run_id':'f'*32,
           'protocol_sha256':p.WAYPOINT_PROTOCOL_SHA256}
    manifest = {'status':'failed','controller':'flynn','requested_device':'cpu','run_id':job['run_id'],
        'scenario':validate_decision(world.SCENARIO,'checker','flynn',profile_sha256=case['profile_sha256']),
        'memory_case':case,'memory_decision_pilot_job':job,'recording_max_bytes':512*p.MiB,
        'memory_decision_pilot_protocol_sha256':job['protocol_sha256']}
    report = {'status':'failed','acquired':False,'goal':False,'continuation_ticks':0,
        'error':{'message':'Real CPU FLYNN prefix did not obtain both open observations and return'}}
    p.admit_prefix_failure(job,supervised,report,manifest)
    for bad in ({**supervised,'status':'timeout'},{**supervised,'failure':{'type':'LogLimit'}}):
        with pytest.raises(ValueError):
            p.admit_prefix_failure(job,bad,report,manifest)


def test_actual_phase_can_checkpoint_multiple_failed_candidates_and_finish(tmp_path,monkeypatch):
    import json
    from pathlib import Path
    module = study()
    repo = Path(module.__file__).resolve().parents[1]
    identity = {'synthetic-software-fixture':True}
    def preflight(repo,assets,history,output,phase,deadline):
        return {'repo':str(repo),'assets':str(assets),'history_root':str(history),
            'output':str(output),'phase_root':str(phase),'source_identity':identity,
            'geometry_valid':True}
    monkeypatch.setattr(module.pilot,'preflight',preflight)
    monkeypatch.setattr(module.pilot,'source_identity',lambda *a:identity)
    monkeypatch.setattr(module.pilot,'launch_owner',lambda *a,**kw:dict(
        status='failed',raw_audit_pass=True,retained_task_failure=True,acquired=False))
    output = tmp_path/'phase'
    assert module.main(['--repo',str(repo),'--assets',str(tmp_path/'assets'),
        '--history-root',str(tmp_path/'history'),'--output',str(output)]) == 0
    receipt = json.loads((output/'execution.json').read_text())
    assert receipt['status'] == 'finished-bounded-attempt'
    assert len(receipt['stages']['development']['attempted']) == 3
    assert receipt['stages']['prerequisites']['status'] == 'unattempted'
    assert receipt['paired_pilot'] == 'unattempted-by-scope'
    assert not list(output.rglob('*.pending'))


def test_terminal_sensor_exception_cannot_be_omitted_or_renamed():
    from palimpsest import memory_decision as decision
    p = study().pilot
    case = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    packet = decision.capture_symbolic(*world.reconstruct_inputs(case,[-2.5,0.,3.141592653589793],0),episode_id='episode-0',tick=0)
    state = decision.initialize(case)
    target = state['supervisor']['waypoint_ids'][0]
    with pytest.raises(decision.CueUnavailable):
        decision.advance_memory(state,packet)
    job = {'case':case,'snapshot_path':None}
    report = {'goal':False,'final_phase':'failed','final_memory':state,'total_ticks':0,
        'outcome':{'type':'CueUnavailable','message':'selected_waypoint_unavailable: '+target}}
    data = {'events':[{'kind':'memory_sensed','episode_step':0,'packet':packet}]}
    p.replay_memory_audit(job,data,None,report,require_terminal_cue=True)
    with pytest.raises(ValueError):
        p.replay_memory_audit(job,{'events':[]},None,report,require_terminal_cue=True)
    with pytest.raises(ValueError):
        p.replay_memory_audit(job,data,None,{**report,'outcome':{
            'type':'CueUnavailable','message':'selected_waypoint_unavailable: other'}},require_terminal_cue=True)


def test_prerequisite_accounting_starts_before_geometry_preparation(tmp_path,monkeypatch):
    module = study()
    now = [100.]
    monkeypatch.setattr(module,'monotonic',lambda:now[0])
    monkeypatch.setattr(module.pilot,'deadline_check',lambda deadline:None)
    monkeypatch.setattr(module.pilot,'file_hash',lambda path:'0'*64)
    original = world.make_case
    def make_case(*a,**kw):
        now[0] += 20.
        return original(*a,**kw)
    monkeypatch.setattr(world,'make_case',make_case)
    observed = []
    monkeypatch.setattr(module.pilot,'write_control',lambda *a:None)
    monkeypatch.setattr(module.pilot,'execute_stage',lambda stage,plan,storage,deadline:
        observed.append(deadline) or {'mandatory_pass':False})
    plan = {'output':str(tmp_path/'development'),'phase_root':str(tmp_path),'geometry_valid':True}
    module.run_prerequisites(plan,world.WAYPOINT_PROFILE_HASHES[0],None,10000.)
    assert observed == [5500.]
