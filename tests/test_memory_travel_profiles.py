"""Travel amendments preserve acquisition while binding actual detour geometry."""
import copy
import pytest
from palimpsest import memory_decision_world as world, memory_decision as decision


def test_registered_travel_cases_use_physical_side_detours_and_actual_lengths():
    old = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    for hash_, offset, cost in zip(world.TRAVEL_PROFILE_HASHES,(.25,.20,.15),
                                  (5.154335509,5.119246573,5.091267197)):
        for mirrored in (False,True):
            case = world.make_case(400,'local_cue','change',mirrored,profile_sha256=hash_)
            assert world.validate_case(case)==case
            assert world.geometry_check(case)['valid']
            preferred = case['closure_subject_id']
            other = next(s for s in case['subjects_by_side'] if s!=preferred)
            sign = -1 if case['subjects_by_side'].index(other)==0 else 1
            assert case['landmarks'][other+'-detour']==[.6,sign*(1+offset)]
            graph = world.public_graph(case)
            assert [r['cost'] for r in graph['routes']]==pytest.approx([5.054335509,cost],abs=1e-9)
            assert graph['routes'][1]['cost']>graph['routes'][0]['cost']
            for i in range(7):
                for subject, old_subject in zip(case['subjects_by_side'],old['subjects_by_side']):
                    assert case['landmarks'][subject+f'-retreat-{i}']==old['landmarks'][old_subject+f'-retreat-{i}']


def test_all_chain_arrival_survey_includes_travel_and_retreat_handoffs():
    case = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    report = world.arrival_analysis(case,include_routes=True)
    pairs={(r['from'],r['to']) for r in report['transitions']}
    a,z=case['subjects_by_side']
    assert (z+'-detour',z+'-exit') in pairs
    assert (a+'-exit',case['common_goal_id']) in pairs
    assert (z+'-inspection',z+'-retreat-0') in pairs
    assert report['continuous_guarantee'] is False
    assert report['native_feasibility']=='unvalidated'
    assert any(r['unsafe_count']>0 for r in report['transitions'])
    legacy=world.arrival_analysis(case)
    assert (z+'-detour',z+'-exit') not in {(r['from'],r['to']) for r in legacy['transitions']}


def test_travel_snapshot_admission_binds_profile_before_allocation():
    from palimpsest.engine import Engine
    import test_memory_decision_engine as ef
    import test_memory_decision as tf
    harness=ef.DecisionEngineTests();harness.setUp()
    try:
        harness.case=world.make_case(0,'local_cue','change',profile_sha256=world.TRAVEL_PROFILE_HASHES[0])
        engine=harness.engine();task=tf.DecisionTests();task.setUp();task.case=harness.case
        engine.memory=task.acquired();engine.total_tick=engine.episode_step=task.tick
        engine.world_task_state['last_tick']=task.tick-1
        engine.env.data.qpos[:]=[*task.position,task.yaw]
        source=harness.snapshot(engine)
        assert Engine._memory_restore(harness.case,world.SCENARIO,'flynn','cpu',source,False,None)[0]==harness.case
        other=world.make_case(0,'local_cue','change',profile_sha256=world.TRAVEL_PROFILE_HASHES[1])
        with pytest.raises(ValueError):Engine._memory_restore(other,world.SCENARIO,'flynn','cpu',source,False,None)
        tampered=copy.deepcopy(harness.case);tampered['landmarks'][tampered['subjects_by_side'][1]+'-detour']=[.6,1.35]
        with pytest.raises(ValueError):world.validate_case(tampered)
    finally:harness.doCleanups()
