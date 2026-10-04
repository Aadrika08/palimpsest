"""Registered waypoint candidates are geometry, never native qualification."""
import copy
import math
import pytest
from palimpsest import memory_decision as decision, memory_decision_world as world


def test_legacy_generator_and_profile_identity_are_preserved():
    assert world.PROFILE_SHA256 == '30bce54fff21ff39910da74bd38f0e2ce4746e29c144e2979c39c0b28d356a5a'
    case = world.make_case(400, 'local_cue', 'no-event')
    assert case['case_sha256'] == '0b2b81eb671f5474279ab1d80b9ad95110dc2698cd92b07f24ab06abb3efb99a'
    assert world.validate_case(case) == case


def test_three_registered_loops_have_visible_separated_successors_and_mirrors():
    hashes = world.WAYPOINT_PROFILE_HASHES
    assert len(hashes) == len(set(hashes)) == 3
    for hash_ in hashes:
        case = world.make_case(400, 'local_cue', 'change', profile_sha256=hash_)
        assert world.validate_case(case) == case
        assert world.geometry_check(case)['valid']
        graph = world.public_graph(case)
        assert graph['profile_sha256'] == hash_
        assert 'xy' not in repr(graph)
        a, b = case['subjects_by_side']
        for index in range(7):
            south, north = (case['landmarks'][subject+f'-retreat-{index}'] for subject in (a,b))
            assert south == [north[0], -north[1]]
        for subject in (a,b):
            ids = [subject+'-inspection']+[subject+f'-retreat-{i}' for i in range(7)]+[case['decision_landmark_id']]
            assert all(math.dist(case['landmarks'][a], case['landmarks'][b]) > .7 for a,b in zip(ids,ids[1:]))
        state = decision.initialize(case)
        assert decision.validate_state(state) == state
        assert world.validate_state(world.initial_state(case))['profile_sha256'] == hash_
    first = world.make_case(400,'local_cue','change',profile_sha256=hashes[0])
    xy = first['landmarks'][first['subjects_by_side'][0]+'-retreat-0']
    assert xy == pytest.approx([-.826538,-1.880110],abs=1e-6)


def test_profile_tampering_is_rejected_at_case_and_snapshot_admission():
    from palimpsest.engine import Engine
    from palimpsest.profiles import validate_decision
    case = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    profile = validate_decision(world.SCENARIO,'checker','flynn',profile_sha256=case['profile_sha256'])
    assert profile['world_protocol_sha256'] == case['profile_sha256']
    assert Engine._memory_restore(case,world.SCENARIO,'flynn','cpu',None,False,None)[0] == case
    bad = copy.deepcopy(case)
    bad['profile_sha256'] = world.WAYPOINT_PROFILE_HASHES[1]
    with pytest.raises(ValueError):
        world.validate_case(bad)
    with pytest.raises(ValueError):
        world.make_case(400,'local_cue','change',profile_sha256='0'*64)
    with pytest.raises(ValueError):
        validate_decision(world.SCENARIO,'checker','flynn',profile_sha256='0'*64)


def test_retained_failure_stays_invisible_while_revised_first_return_target_is_visible():
    pose = [-.8503412008285522,-1.120007872581482,-.6957413055440772]
    old = world.make_case(400,'local_cue','no-event')
    old_target = old['subjects_by_side'][0]+'-retreat-1'
    for hash_ in (world.PROFILE_SHA256,*world.WAYPOINT_PROFILE_HASHES):
        case = world.make_case(400,'local_cue','no-event',profile_sha256=hash_)
        packet = decision.capture_symbolic(*world.reconstruct_inputs(case,pose,101,gate_result='not_requested'),episode_id='episode-0',tick=101)
        ids = {x['id'] for x in packet['landmarks']}
        if hash_ == world.PROFILE_SHA256:
            assert old_target not in ids
        else:
            assert case['subjects_by_side'][0]+'-retreat-0' in ids


def test_arrival_analysis_reports_unsafe_headings_without_claiming_native_feasibility():
    case = world.make_case(400,'local_cue','change',profile_sha256=world.WAYPOINT_PROFILE_HASHES[0])
    report = world.arrival_analysis(case)
    assert report['native_feasibility'] == 'unvalidated'
    assert report['continuous_guarantee'] is False
    assert report['position_step_m'] == .05
    assert report['heading_step_degrees'] == 5
    assert any(x['unsafe_count'] > 0 and x['unsafe_examples'] for x in report['transitions'])
    assert all(x['tested_count'] == x['visible_count']+x['unsafe_count'] for x in report['transitions'])
