"""Synthetic evidence checks for the family-v3 evaluator-only oracle."""
import copy
import math
from unittest.mock import patch

import pytest

from palimpsest import memory, memory_decision as decision
from palimpsest import memory_decision_world as world, memory_experiment
from scripts import memory_family_oracle_v3 as oracle
from scripts.memory_family_oracle_v3 import (
    oracle_evidence,
    selector_resource,
    validate_oracle_evidence,
)


def _world_record(case, pose, *, closed_side=None):
    obstacles = copy.deepcopy(world.PROFILE['obstacles'])
    if closed_side is not None:
        obstacles[len(world.POSTS) + closed_side] = world.CLOSED_GATES[closed_side].copy()
    return {'arena': 7.0, 'pose': list(pose), 'goal': [*case['goal_xy'], .25],
            'obstacles': [[*xy, .4] for xy in obstacles]}


def _event(kind, episode_step, **values):
    return {'kind': kind, 'episode': 0, 'episode_step': episode_step,
            'tick': episode_step, **values}


def _bind_events(events, run_id):
    for sequence, event in enumerate(events):
        event['sequence'] = sequence
        event['run_id'] = run_id


def _packet(case, pose, tick, *, event_tick=None, gate_result='not_requested'):
    inputs = world.reconstruct_inputs(
        case, pose, tick, event_tick=event_tick, gate_result=gate_result)
    return decision.capture_symbolic(*inputs, episode_id='episode-0', tick=tick)


def _acquire(case):
    state, tick = decision.initialize(case), 0
    pose = list(case['start_pose'])
    events = [_event('episode_started', 0, seed=case['seed'],
                     world=_world_record(case, pose))]
    rows = []
    while state['supervisor']['phase'] != 'await_decision':
        assert tick < 40
        packet = _packet(case, pose, tick)
        state, _, audit = decision.advance_memory(state, packet)
        next_pose = pose.copy()
        if state['supervisor']['phase'] != 'await_decision':
            target = state['supervisor']['waypoint_ids'][state['supervisor']['waypoint_index']]
            xy = case['landmarks'][target]
            if xy != pose[:2]:
                next_pose[2] = math.atan2(xy[1] - pose[1], xy[0] - pose[0])
            next_pose[:2] = xy
        rows.append({'episode': 0, 'tick': tick, 'pose': pose.copy(),
                     'next_pose': next_pose.copy()})
        events.append(_event('memory_sensed', tick, packet=packet))
        events.extend(_event('memory_decision', tick, detail=item) for item in audit)
        pose = next_pose
        tick += 1
    return state, tick, pose, events, rows


def _application(case, state, boundary, world_state, run_id):
    return {'schema_version': 8, 'source_run_id': run_id,
        'event_prefix': {'sha256': '1' * 64, 'size_bytes': 1, 'event_count': boundary},
        'teacher_reset_identity': None, 'controller': 'flynn', 'episode': 0,
        'total_tick': boundary, 'revision': 0, 'eyes': {'left': True, 'right': True},
        'scenario': world.SCENARIO, 'texture': 'checker', 'episode_step': boundary,
        'phase': 'paused', 'manual_action': [0.0, 0.0],
        'metrics': {'reward': 0.0, 'contact_ticks': 0, 'path_length': 0.0},
        'last_outcome': None, 'seed': case['seed'], 'episode_finished': False,
        'pending_commands': [], 'session_exhausted': False, 'recording_failed': False,
        'receipts': {}, 'original_commands': {}, 'memory': copy.deepcopy(state),
        'world_task_state': copy.deepcopy(world_state),
        'controller_tensors': {'graph_buffers': '2' * 64, 'parameters': '3' * 64},
        'execution_mode': 'policy', 'task_state': None}


def _acquired_hash(application, configured):
    admitted = copy.deepcopy(application)
    admitted['memory'] = copy.deepcopy(configured)
    admitted.pop('source_run_id')
    admitted.pop('event_prefix')
    admitted['memory'].pop('u')
    admitted['memory'].pop('selector')
    return memory.sha256(admitted)


def evidence(row=4, kind='change'):
    case = world.make_family_case('development', 0, row, kind)
    acquired, boundary, pose, source_events, source_rows = _acquire(case)
    source_events.append(_event('memory_acquired_boundary', boundary,
        boundary_tick=boundary,
        acquired_evidence=copy.deepcopy(acquired['supervisor']['acquired_evidence'])))
    source_world = world.initial_state(case)
    source_world['last_tick'] = boundary - 1
    source_world = world.validate_state(source_world)
    bindings = {'protocol_sha256': '4' * 64, 'plan_sha256': '5' * 64,
        'source_identity_sha256': '6' * 64,
        'source': {'run_id': '00000000000000000000000000000001',
                   'recording_sha256': '7' * 64,
                   'report_sha256': '8' * 64, 'snapshot_sha256': '9' * 64},
        'post': {'run_id': '00000000000000000000000000000002',
                 'recording_sha256': 'a' * 64,
                 'report_sha256': 'b' * 64, 'source_snapshot_sha256': '9' * 64,
                 'condition': 'own'}}
    application = _application(case, acquired, boundary, source_world,
                               bindings['source']['run_id'])
    history = memory_experiment.make_history(200, case['regime'])
    fitted = memory.fit(history)
    history_bundle_sha256 = memory.sha256({'e': history, 'u': fitted})
    selector = {'version': 1, 'condition': 'own', 'limit': 1, 'resource': None,
        'resource_sha256': memory.sha256(None),
        'provenance_sha256': history_bundle_sha256}
    configured = decision.configure_selector(
        acquired, selector, fitted)
    bindings['post']['history_sha256'] = memory.sha256(history)
    bindings['post']['history_bundle_sha256'] = history_bundle_sha256
    bindings['post']['selector_sha256'] = memory.sha256(configured['selector'])
    bindings['post']['u_sha256'] = memory.sha256(configured['u'])
    acquired_sha = _acquired_hash(application, configured)
    post_world = world.arm(source_world, boundary, acquired_sha)
    schedule = {'boundary_tick': boundary, 'event_tick': post_world['event_tick'],
                'decision_tick': post_world['decision_tick'],
                'acquired_state_sha256': acquired_sha}
    retained = {key: value for key, value in acquired.items()
                if key not in ('u', 'selector')}
    post_events = [
        _event('application_restored', boundary,
               parent_run_id=bindings['source']['run_id'],
               parent_event_prefix=copy.deepcopy(application['event_prefix']),
               world=_world_record(case, pose), revision=application['revision'],
               eyes=copy.deepcopy(application['eyes'])),
        _event('memory_selector_configured', boundary,
               selector=copy.deepcopy(configured['selector']),
               u=copy.deepcopy(configured['u']),
               retained_memory_sha256=memory.sha256(retained)),
        _event('memory_decision_armed', boundary, schedule=schedule),
    ]
    armed = decision.arm(configured, boundary)
    post_rows = []
    gate_result = 'closed' if kind == 'change' else 'not_requested'
    for tick in range(boundary, post_world['decision_tick'] + 1):
        post_world['last_tick'] = tick
        if tick == post_world['event_tick']:
            post_world.update(applied=True, cue_state=1, gate_result=gate_result)
            post_events.append(_event('memory_world_changed', tick,
                detail={'kind': 'memory_cue_changed', 'tick': tick,
                        'cue_id': case['cue_id'], 'before': 0, 'after': 1}))
            if kind == 'change':
                side = case['subjects_by_side'].index(case['closure_subject_id'])
                intervention = {'kind': 'move_obstacle',
                    'index': len(world.POSTS) + side,
                    'old': {'xy': world.PARKED_GATES[side].copy()},
                    'new': {'xy': world.CLOSED_GATES[side].copy()},
                    'simulation_time': float(tick)}
                post_events.append(_event('memory_world_changed', tick,
                    detail={'kind': 'memory_gate_applied', 'tick': tick,
                        'subject_id': case['closure_subject_id'],
                        'intervention': copy.deepcopy(intervention)}))
                post_events.append(_event('intervention', tick,
                    change=intervention, origin='memory_world_schedule'))
        packet = _packet(case, pose, tick, event_tick=post_world['event_tick'],
                         gate_result=gate_result)
        armed, _, audit = decision.advance_memory(armed, packet)
        post_rows.append({'episode': 0, 'tick': tick, 'pose': pose.copy(),
                          'next_pose': pose.copy()})
        post_events.append(_event('memory_sensed', tick, packet=packet))
        post_events.extend(_event('memory_decision', tick, detail=item)
                           for item in audit)
    post_world = world.validate_state(post_world)
    assert all(passage['passability'] == 'unobserved'
               for event in post_events if event['kind'] == 'memory_sensed'
               for passage in event['packet']['passages'])
    _bind_events(source_events, bindings['source']['run_id'])
    _bind_events(post_events, bindings['post']['run_id'])
    return {'case': case, 'source_application': application,
        'source_events': source_events, 'source_rows': source_rows,
        'post_events': post_events, 'post_rows': post_rows,
        'post_world_state': post_world, 'bindings': bindings}


def _args(sample):
    return tuple(sample[key] for key in ('case', 'source_application',
        'source_events', 'source_rows', 'post_events', 'post_rows',
        'post_world_state', 'bindings'))


def _proof(sample):
    return oracle_evidence(*_args(sample))


def _reject(sample):
    with pytest.raises(ValueError):
        _proof(sample)


def test_all_family_rows_kinds_schedules_and_sides_recompute_gold_without_fit_or_select():
    schedules, closure_sides = set(), set()
    for row in range(48):
        for kind in memory_experiment.KINDS:
            sample = evidence(row, kind)
            case = sample['case']
            schedule = world.registered_profile(case['profile_sha256'])['arm_schedule']
            schedules.add((schedule['event_offset'], schedule['decision_offset']))
            if kind == 'change':
                closure_sides.add(case['subjects_by_side'].index(case['closure_subject_id']))
                expected = [next(fact['id'] for fact in case['facts']
                    if fact['subject_id'] == case['closure_subject_id'])]
            else:
                expected = []
            real_selection = oracle.selection_for_condition
            def donor_selection(condition, *args, **kwargs):
                assert condition == 'own'
                return real_selection(condition, *args, **kwargs)
            with patch.object(memory, 'fit', side_effect=AssertionError('oracle cannot fit')), \
                 patch.object(oracle, 'selection_for_condition', side_effect=donor_selection):
                proof = _proof(sample)
                assert proof['gold_target_ids'] == expected, (row, kind)
                assert validate_oracle_evidence(proof, *_args(sample)) == proof
                assert selector_resource(
                    'oracle', proof, **sample) == {
                        'resource': expected,
                        'resource_sha256': memory.sha256(expected),
                        'provenance_sha256': memory.sha256(proof),
                    }
    assert schedules == {(1, 2), (2, 3)}
    assert closure_sides == {0, 1}


def test_source_evidence_packets_schedule_world_gate_trigger_bindings_and_proof_tampering_reject():
    original = evidence()

    sample = copy.deepcopy(original)
    sample['source_application']['memory']['m']['facts'][0]['evidence']['id'] = 'forged-evidence'
    _reject(sample)

    sample = copy.deepcopy(original)
    passage = next(p for event in sample['source_events']
        if event['kind'] == 'memory_sensed' for p in event['packet']['passages']
        if p['passability'] == 'open')
    passage['passability'] = 'blocked'
    _reject(sample)

    sample = copy.deepcopy(original)
    sensed = [event for event in sample['source_events']
              if event['kind'] == 'memory_sensed']
    first, last = (sample['source_events'].index(event)
                   for event in (sensed[0], sensed[-1]))
    sample['source_events'][first], sample['source_events'][last] = (
        sample['source_events'][last], sample['source_events'][first])
    _bind_events(sample['source_events'], sample['bindings']['source']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['post_events']
         if event['kind'] == 'memory_decision_armed')['schedule']['decision_tick'] += 1
    _reject(sample)

    sample = copy.deepcopy(original)
    armed = next(event for event in sample['post_events']
                 if event['kind'] == 'memory_decision_armed')
    sample['post_events'].remove(armed)
    sample['post_events'].append(armed)
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    future = [event for event in sample['post_events']
              if event['kind'] in ('memory_world_changed', 'intervention')]
    sample['post_events'] = [event for event in sample['post_events']
                             if event not in future]
    restored_index = next(index for index, event in enumerate(sample['post_events'])
                          if event['kind'] == 'application_restored')
    sample['post_events'][restored_index + 1:restored_index + 1] = future
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['post_world_state']['last_tick'] -= 1
    _reject(sample)

    sample = copy.deepcopy(original)
    restored = next(event for event in sample['post_events']
                    if event['kind'] == 'application_restored')
    restored['world']['obstacles'][0][0] += .1
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['post_events']
         if event['kind'] == 'application_restored')['revision'] += 1
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['post_events']
         if event['kind'] == 'application_restored')['eyes']['left'] = False
    _reject(sample)

    sample = copy.deepcopy(original)
    gate = next(event['detail'] for event in sample['post_events']
                if event['kind'] == 'memory_world_changed'
                and event['detail']['kind'] == 'memory_gate_applied')
    gate['intervention']['new']['xy'][0] += .1
    _reject(sample)

    sample = copy.deepcopy(original)
    trigger = next(event['detail']['trigger'] for event in sample['post_events']
                   if event['kind'] == 'memory_decision'
                   and event['detail']['kind'] == 'memory_trigger')
    trigger['before_observation_id'] = 'forged-cue-observation'
    _reject(sample)

    sample = copy.deepcopy(original)
    trigger_event = next(event for event in sample['post_events']
        if event['kind'] == 'memory_decision'
        and event['detail']['kind'] == 'memory_trigger')
    sample['post_events'].remove(trigger_event)
    packet_index = next(index for index, event in enumerate(sample['post_events'])
        if event['kind'] == 'memory_sensed'
        and event['episode_step'] == sample['post_world_state']['event_tick'])
    sample['post_events'].insert(packet_index, trigger_event)
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    bridge = next(event for event in sample['post_events']
                  if event['kind'] == 'memory_decision'
                  and event['detail']['kind'] == 'memory_bridge')
    sample['post_events'].remove(bridge)
    packet_index = next(index for index, event in enumerate(sample['post_events'])
        if event['kind'] == 'memory_sensed'
        and event['episode_step'] == bridge['episode_step'])
    sample['post_events'].insert(packet_index, bridge)
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['bindings']['source']['run_id'] = '00000000000000000000000000000003'
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['bindings']['post']['run_id'] = 'post-not-a-uuid'
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['source_application']['recording_failed'] = True
    _reject(sample)

    sample = copy.deepcopy(original)
    command = {'id': 'queued', 'kind': 'step', 'expected_state': 'paused',
               'expected_episode': 0, 'payload': {}}
    sample['source_application']['pending_commands'] = [command]
    sample['source_application']['original_commands'] = {'queued': command}
    sample['source_application']['receipts'] = {
        'queued': {'id': 'queued', 'status': 'queued'}}
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['source_events']
         if event['kind'] == 'memory_sensed').pop('tick')
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['source_events']
         if event['kind'] == 'episode_started').pop('seed')
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['source_rows'][0]['next_pose'][0] += .1
    _reject(sample)

    sample = copy.deepcopy(original)
    next(event for event in sample['source_events']
         if event['kind'] == 'episode_started')['world']['pose'][0] += .1
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['post_rows'][0]['next_pose'][0] += .1
    _reject(sample)

    sample = copy.deepcopy(original)
    configured = next(event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured')
    other_relation = next(relation for relation in memory.RELATIONS
                          if relation != sample['case']['regime'])
    other_history = memory_experiment.make_history(300, other_relation)
    configured['u'] = memory.fit(other_history)
    sample['bindings']['post']['u_sha256'] = memory.sha256(configured['u'])
    sample['bindings']['post']['history_sha256'] = memory.sha256(other_history)
    _reject(sample)

    sample = copy.deepcopy(original)
    configured = next(event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured')
    configured['u']['provenance']['method'] = 'hand-authored-v1'
    sample['bindings']['post']['u_sha256'] = memory.sha256(configured['u'])
    _reject(sample)

    sample = copy.deepcopy(original)
    configured = next(event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured')
    configured['selector']['provenance_sha256'] = 'c' * 64
    sample['bindings']['post']['selector_sha256'] = memory.sha256(configured['selector'])
    _reject(sample)

    sample = copy.deepcopy(original)
    selection = next(event['detail']['selection'] for event in sample['post_events']
                     if event['kind'] == 'memory_decision'
                     and event['detail']['kind'] == 'memory_selection')
    selection['target_ids'] = [next(fact['id'] for fact in sample['case']['facts']
                                    if fact['id'] not in selection['target_ids'])]
    _reject(sample)

    sample = copy.deepcopy(original)
    commitment = next(event['detail'] for event in sample['post_events']
                      if event['kind'] == 'memory_decision'
                      and event['detail']['kind'] == 'memory_commitment')
    commitment['route_id'] = 'forged-route'
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['post_events'][0]['run_id'] = sample['bindings']['source']['run_id']
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['post_events'][1]['sequence'] += 1
    _reject(sample)

    sample = copy.deepcopy(original)
    sample['post_events'].append({'kind': 'memory_decision', 'episode': 0,
        'tick': sample['post_world_state']['last_tick'],
        'detail': {'kind': 'forged-without-boundary'}})
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    tick = sample['post_world_state']['last_tick']
    sample['post_events'].append(_event('runtime_failure', tick, error={
        'reason': 'runtime_failure', 'episode': 0, 'steps': tick,
        'type': 'ValueError', 'message': 'forged', 'policy_diagnostics': None}))
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    proof = _proof(original)
    bad = copy.deepcopy(proof)
    bad['gold_target_ids'] = []
    with pytest.raises(ValueError):
        validate_oracle_evidence(bad, *_args(original))
    bad = copy.deepcopy(proof)
    bad['bindings']['plan_sha256'] = 'c' * 64
    with pytest.raises(ValueError):
        selector_resource('oracle', bad, **original)

    for mode in ('missing', 'wrong', 'duplicate'):
        sample = copy.deepcopy(original)
        configured = [event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured']
        if mode == 'missing':
            sample['post_events'].remove(configured[0])
        elif mode == 'wrong':
            configured[0]['selector']['condition'] = 'swapped'
            sample['bindings']['post']['selector_sha256'] = memory.sha256(
                configured[0]['selector'])
        else:
            sample['post_events'].append(copy.deepcopy(configured[0]))
        _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
        _reject(sample)


def test_rejected_duplicate_gate_edits_and_fresh_passage_observation_reject():
    original = evidence()
    sample = copy.deepcopy(original)
    gate_event = next(event for event in sample['post_events']
        if event['kind'] == 'memory_world_changed'
        and event['detail']['kind'] == 'memory_gate_applied')
    gate_event['detail'] = {'kind': 'memory_gate_rejected',
        'tick': gate_event['episode_step'],
        'subject_id': sample['case']['closure_subject_id'], 'reason': 'rejected'}
    sample['post_world_state']['gate_result'] = 'rejected'
    _reject(sample)

    sample = copy.deepcopy(original)
    gate_event = next(event for event in sample['post_events']
        if event['kind'] == 'memory_world_changed'
        and event['detail']['kind'] == 'memory_gate_applied')
    sample['post_events'].append(copy.deepcopy(gate_event))
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    _reject(sample)

    sample = copy.deepcopy(original)
    event_tick = sample['post_world_state']['event_tick']
    row = next(row for row in sample['post_rows'] if row['tick'] == event_tick)
    fact = next(fact for fact in sample['case']['facts']
                if fact['subject_id'] == sample['case']['closure_subject_id'])
    xy = sample['case']['landmarks'][fact['inspection_landmark_id']]
    cue = sample['case']['cue_xy']
    pose = [*xy, math.atan2(cue[1] - xy[1], cue[0] - xy[0])]
    row['pose'] = row['next_pose'] = pose
    sensed = next(event for event in sample['post_events']
        if event['kind'] == 'memory_sensed' and event['episode_step'] == event_tick)
    sensed['packet'] = _packet(sample['case'], pose, event_tick,
        event_tick=event_tick, gate_result='closed')
    assert sensed['packet']['cues']
    assert any(p['passability'] != 'unobserved' for p in sensed['packet']['passages'])
    _reject(sample)


def test_no_event_has_no_trigger_or_selection_and_non_oracle_cannot_receive_proof():
    sample = evidence(kind='no-event')
    proof = _proof(sample)
    details = [event['detail'] for event in sample['post_events']
               if event['kind'] == 'memory_decision']
    assert proof['trigger'] is None
    assert proof['gold_target_ids'] == []
    assert not any(detail['kind'] in ('memory_trigger', 'memory_selection')
                   for detail in details)

    for condition in memory_experiment.CONDITIONS:
        if condition == 'oracle':
            continue
        assert selector_resource(condition) == {}
        with pytest.raises(ValueError):
            selector_resource(condition, proof)
        with pytest.raises(ValueError):
            selector_resource(condition, case=sample['case'])
    with pytest.raises(ValueError):
        selector_resource('oracle')

    for detail in ({'kind': 'memory_trigger', 'trigger': {'forged': True}},
                   {'kind': 'memory_selection', 'selection': {'forged': True}}):
        bad = copy.deepcopy(sample)
        tick = bad['post_world_state']['decision_tick']
        bad['post_events'].append(_event('memory_decision', tick, detail=detail))
        _bind_events(bad['post_events'], bad['bindings']['post']['run_id'])
        with pytest.raises(ValueError):
            _proof(bad)


def test_native_terminal_sensor_only_tick_is_admitted_only_with_its_failure():
    sample = evidence()
    tick = sample['post_world_state']['last_tick'] + 1
    configured = next(event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured')
    row_packets = [event['packet'] for event in sample['post_events']
                   if event['kind'] == 'memory_sensed']
    def failed_row(state, packet):
        state = copy.deepcopy(state)
        state['supervisor']['phase'] = 'failure'
        return state, [1.0, 0.0], []
    with patch.object(decision, 'advance_memory', side_effect=failed_row), \
         pytest.raises(ValueError, match='terminal supervisor decision'):
        oracle._replay_post(sample['source_application']['memory'],
            configured['selector'], configured['u'],
            sample['source_application']['episode_step'], row_packets,
            sample['post_events'], None)
    state = decision.configure_selector(sample['source_application']['memory'],
        configured['selector'], configured['u'])
    state = decision.arm(state, sample['source_application']['episode_step'])
    packets = {event['episode_step']: event['packet'] for event in sample['post_events']
               if event['kind'] == 'memory_sensed'}
    for row in sample['post_rows']:
        state, _, _ = decision.advance_memory(state, packets[row['tick']])
    supervisor = state['supervisor']
    unavailable = supervisor['waypoint_ids'][supervisor['waypoint_index']]
    pose = sample['post_rows'][-1]['next_pose'].copy()
    pose[2] = math.remainder(pose[2] + math.pi, 2 * math.pi)
    sample['post_rows'][-1]['next_pose'] = pose
    packet = _packet(sample['case'], pose, tick,
        event_tick=sample['post_world_state']['event_tick'], gate_result='closed')
    visible = {item['id'] for item in packet['landmarks']}
    assert unavailable not in visible
    sample['post_events'].append(_event('memory_sensed', tick, packet=packet))
    sample['post_events'].append(_event('runtime_failure', tick, error={
        'reason': 'runtime_failure', 'episode': 0, 'steps': tick,
        'type': 'CueUnavailable',
        'message': 'selected_waypoint_unavailable: ' + unavailable,
        'policy_diagnostics': None}))
    sample['post_world_state']['last_tick'] = tick
    _bind_events(sample['post_events'], sample['bindings']['post']['run_id'])
    assert _proof(sample)['gold_target_ids']

    bad = copy.deepcopy(sample)
    bad['post_events'] = [event for event in bad['post_events']
                          if event['kind'] != 'runtime_failure']
    _bind_events(bad['post_events'], bad['bindings']['post']['run_id'])
    _reject(bad)

    bad = copy.deepcopy(sample)
    later = tick + 1
    bad['post_events'].append(_event('memory_sensed', later, packet=_packet(
        bad['case'], pose, later, event_tick=bad['post_world_state']['event_tick'],
        gate_result='closed')))
    _bind_events(bad['post_events'], bad['bindings']['post']['run_id'])
    _reject(bad)

    bad = copy.deepcopy(sample)
    bad['post_events'].append(_event('memory_decision', tick, detail={
        'kind': 'memory_bridge', 'tick': tick, 'landmark_id': unavailable,
        'bearing': [1.0, 0.0], 'phase': 'follow_route'}))
    _bind_events(bad['post_events'], bad['bindings']['post']['run_id'])
    _reject(bad)

    bad = copy.deepcopy(sample)
    failure = next(event for event in bad['post_events']
                   if event['kind'] == 'runtime_failure')
    failure['error'].update(type='ValueError', message='unrelated failure')
    bad['post_events'].insert(bad['post_events'].index(failure),
        _event('memory_decision', tick, detail={'kind': 'memory_transition',
            'tick': tick, 'from': 'follow_route', 'to': 'failure',
            'reason': None, 'route_id': 'forged', 'waypoint_index': 0}))
    _bind_events(bad['post_events'], bad['bindings']['post']['run_id'])
    _reject(bad)
