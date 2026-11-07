"""Authored decoded evidence only; no held source, owner, model or native run."""
import copy
import hashlib
import importlib
import json
import math
import time
from unittest.mock import patch

import numpy as np
import pytest

from palimpsest import memory, memory_decision as decision, memory_decision_world as world
from palimpsest import memory_experiment, memory_transition_vnext as transition
from palimpsest.profiles import validate_decision
from test_memory_family_oracle_v3 import _acquire, _application, _bind_events, _event, _world_record
from test_memory_family_raw_audit_v4 import _policy_row


SOURCE = '00000000-0000-0000-0000-000000000001'
OWNER = '00000000-0000-0000-0000-000000000002'
CONDITIONS = memory_experiment.CONDITIONS


def api():
    try:
        return importlib.import_module('scripts.memory_family_terminal_audit_vnext')
    except ModuleNotFoundError:
        pytest.fail('Task3a pure terminal proof API is missing', pytrace=False)


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()


def descriptor(path, payload):
    return {'path': path, 'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def rebind(sample):
    raw, context = sample['raw'], sample['context']
    for name, payload in (
        ('context', memory.canonical_bytes(context)),
        ('raw_manifest', encoded(raw['manifest'])),
        ('raw_events', b''.join(encoded(e) for e in raw['events'])),
        ('worker_report', memory.canonical_bytes(raw['worker_report'])),
    ):
        raw['descriptors'][name] = descriptor(raw['descriptors'][name]['path'], payload)
    return sample


def fixture(condition='oracle', kind='change', count=2, *, normal=False, selected_failure=False, supervisor_failure=False, delayed_route=False, empty_snapshot=False):
    case = world.make_family_case('development', 0, 4, kind)
    source, boundary, pose, source_events, source_projection = _acquire(case)
    source_events.append(_event('memory_acquired_boundary', boundary, boundary_tick=boundary,
        acquired_evidence=copy.deepcopy(source['supervisor']['acquired_evidence'])))
    _bind_events(source_events, SOURCE)
    source_world = world.initial_state(case)
    source_world['last_tick'] = boundary - 1
    application = _application(case, source, boundary, source_world, SOURCE)
    source_payload = b''.join(encoded(e) for e in source_events)
    application['event_prefix'] = {'sha256': hashlib.sha256(source_payload).hexdigest(),
        'size_bytes': len(source_payload), 'event_count': len(source_events)}
    d = descriptor('authored/profile.json', b'authored proposed profile')
    context = {'schema': transition.CONTEXT_SCHEMA,
        **{k: copy.deepcopy(d) for k in transition._DESCRIPTOR_ROLES},
        'source_application_sha256': memory.sha256(application),
        'source_m_sha256': memory.sha256(source['m']), 'source_world_sha256': memory.sha256(source_world),
        'source_run_id': SOURCE, 'case_id': case['case_id'], 'case_sha256': memory.sha256(case),
        'kind': kind, 'run_id': OWNER, 'condition': condition,
        'condition_resources_sha256': 'a' * 64,
        'source_invariant_sha256': transition.terminal_condition_invariant_vnext(application),
        'schedule': {'boundary_tick': boundary,
            'event_tick': None if kind == 'no-event' else boundary + world.registered_profile(case['profile_sha256'])['arm_schedule']['event_offset'],
            'decision_tick': boundary + world.registered_profile(case['profile_sha256'])['arm_schedule']['decision_offset']}}
    if empty_snapshot:
        context['source_snapshot'] = descriptor('authored/snapshot.snp', b'')
    resource = [] if condition == 'oracle' else {'version': 1, 'episodes': []} if condition == 'retrieval' else None
    config = {'version': 1, 'condition': condition, 'limit': 1, 'resource': resource,
        'resource_sha256': memory.sha256(resource),
        'provenance_sha256': transition.pending_provenance_vnext(context) if condition == 'oracle' else 'b' * 64}
    u = memory.artifact('local_cue') if condition == 'hand-authored' else memory.artifact()
    context['condition_resources_sha256'] = memory.sha256({'selector': config, 'u': u})
    state = transition.configure_terminal_condition_vnext(source, config, u, context=context)
    state = transition.arm_terminal_state_vnext(state, boundary_tick=boundary, context=context)
    post_world = world.arm(source_world, boundary, context['source_invariant_sha256'])
    schedule = {**context['schedule'], 'acquired_state_sha256': context['source_invariant_sha256']}
    events = []
    def emit(kind, tick, **values):
        event = _event(kind, tick, **values)
        event.update(run_id=OWNER, sequence=len(events))
        events.append(event)
        return {'sequence': event['sequence'], 'sha256': memory.sha256(event)}
    # Source and condition poses are authored row evidence, not native placement.
    if count == 0:
        pose = [100., 100., 0.]
        source_projection[-1]['next_pose'] = pose.copy()
    emit('application_restored', boundary, parent_run_id=SOURCE,
        parent_event_prefix=application['event_prefix'], world=_world_record(case, pose),
        revision=application['revision'], eyes=application['eyes'])
    retained = {k: v for k, v in source.items() if k not in ('u', 'selector')}
    emit('memory_selector_configured', boundary, selector=config, u=u, retained_memory_sha256=memory.sha256(retained))
    emit('memory_decision_armed', boundary, schedule=schedule)
    binding = transition.OracleBinding(source['m'], case, source_world) if condition == 'oracle' else None
    job = descriptor('authored/job.json', b'actual full job bytes deliberately unavailable in pure API')
    rows, chain = [], (0, memory.sha256(context))
    refs = {'cue_event': None, 'gate_event': None, 'intervention_event': None}
    results = []
    if selected_failure:
        assert count == 1 and kind != 'no-event'
        target = state['supervisor']['waypoint_ids'][state['supervisor']['waypoint_index']]
        poses = ([float(x), float(y), float(a)] for x in np.arange(-6., 6.1, .5)
            for y in np.arange(-6., 6.1, .5) for a in (0., math.pi / 2, math.pi, -math.pi / 2))
        failing_pose = None
        for candidate in poses:
            packet = decision.capture_symbolic(*world.reconstruct_inputs(case, candidate, boundary + 1,
                event_tick=post_world['event_tick'], gate_result='closed' if kind == 'change' else 'not_requested'),
                episode_id='episode-0', tick=boundary + 1)
            if packet['cues'] and target not in {x['id'] for x in packet['landmarks']} and all(p['passability'] == 'unobserved' for p in packet['passages']):
                failing_pose = candidate
                break
        assert failing_pose is not None, 'authored geometry must expose local selection then missing target'
    for offset in range(count if normal else count + 1):
        tick = boundary + offset
        post_world['last_tick'] = tick
        if tick == post_world['event_tick']:
            post_world.update(applied=True, cue_state=1, gate_result='closed' if kind == 'change' else 'not_requested')
            refs['cue_event'] = emit('memory_world_changed', tick,
                detail={'kind': 'memory_cue_changed', 'tick': tick, 'cue_id': case['cue_id'], 'before': 0, 'after': 1})
            if kind == 'change':
                side = case['subjects_by_side'].index(case['closure_subject_id'])
                edit = {'kind': 'move_obstacle', 'index': len(world.POSTS) + side,
                    'old': {'xy': world.PARKED_GATES[side].copy()}, 'new': {'xy': world.CLOSED_GATES[side].copy()},
                    'simulation_time': float(tick)}
                refs['gate_event'] = emit('memory_world_changed', tick,
                    detail={'kind': 'memory_gate_applied', 'tick': tick, 'subject_id': case['closure_subject_id'], 'intervention': edit})
                refs['intervention_event'] = emit('intervention', tick, change=edit, origin='memory_world_schedule')
        private, sensed_pose, circles = world.audit_inputs(post_world, pose)
        packet = decision.capture_symbolic(private, sensed_pose, circles, episode_id='episode-0', tick=tick)
        sensed = emit('memory_sensed', tick, packet=packet)
        reach = {**copy.deepcopy(refs), 'sensed_event': sensed, 'before_occupancy': None,
            'after_occupancy': None, 'actual_circles': circles}
        result = transition.advance_transition_vnext(state, packet, context=context,
            oracle_binding=binding, reach=reach, job_sha256=job['sha256'], chain=chain)
        results.append(result)
        if result.witness is not None:
            emit('memory_transition_witness_vnext', tick, witness=result.witness)
            chain = (chain[0] + 1, memory.sha256(result.witness))
        if result.status == 'raised':
            error = result.witness['exception']
            outcome = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick, **error, 'policy_diagnostics': {}}
            emit('runtime_failure', tick, error=outcome)
            break
        assert result.status in ('ordinary-return', 'witnessed-return'), result.status
        state = result.proposed_state
        if result.witness is not None:
            emit('memory_transition_commit_vnext', tick, commit={'schema': transition.COMMIT_SCHEMA,
                'context_sha256': memory.sha256(context), 'witness_sha256': memory.sha256(result.witness),
                'tick': tick, 'memory_sha256': memory.sha256(state), 'lifecycle': state['terminal_lifecycle']})
        for detail in result.decisions:
            emit('memory_decision', tick, detail=detail, route_anchor={'stage': 'pre-control', 'xy': pose[:2]})
        emit('memory_inspected', tick, memory=transition.inspect_terminal_state_vnext(state, context=context))
        if state['supervisor']['phase'] == 'failure':
            assert supervisor_failure and offset == count
            outcome = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick, 'type': 'ValueError',
                'message': 'Memory-v2 supervisor failure: ' + state['supervisor']['failure_reason'], 'policy_diagnostics': {}}
            emit('runtime_failure', tick, error=outcome)
            break
        emit('memory_cue', tick, bearing=result.bearing, raw_upstream_bearing=[1., 0.])
        next_pose = pose.copy()
        if delayed_route and state['supervisor']['waypoint_deadline_tick'] - tick == 2:
            sup = state['supervisor']
            target = sup['waypoint_ids'][sup['waypoint_index']]
            xy = case['landmarks'][target]
            next_target = sup['waypoint_ids'][min(sup['waypoint_index'] + 1, len(sup['waypoint_ids']) - 1)]
            after = case['landmarks'][next_target]
            next_pose = [*xy, math.atan2(after[1] - xy[1], after[0] - xy[0]) / 2.]
        if not normal and not supervisor_failure and offset == count - 1:
            next_pose = failing_pose.copy() if selected_failure else [100., 100., 0.]
        row = {'episode': 0, 'tick': tick, 'pose': pose.copy(), 'next_pose': next_pose.copy()}
        policy, arrays = _policy_row(row, OWNER)
        policy['sensors']['wind_direction'] = result.bearing.copy()
        arrays['sensors'] = np.asarray([0., 0., *result.bearing], np.float32)
        from palimpsest import snapshots
        policy['observation_sha256'] = snapshots.state_digest({'cam_left': arrays['cam_left'], 'cam_right': arrays['cam_right'], 'sensors': policy['sensors']})
        emit('neural_policy_call', tick, **{k: v for k, v in policy.items() if k not in ('run_id', 'episode', 'episode_step', 'tick')})
        rows.append({'episode': 0, 'tick': tick, **arrays})
        pose = next_pose
    if normal:
        outcome = {'reason': 'time_limit' if count == 900 else 'stalled', 'episode': 0, 'steps': boundary + count, 'final_distance': 10.}
        final_phase, status = ('truncated' if count == 900 else 'terminated'), 'completed'
    else:
        assert results[-1].status == ('witnessed-return' if supervisor_failure else 'raised'), 'authored natural terminal must actually terminate'
        final_phase, status = 'failed', 'failed'
    metrics = {'reward': 0., 'contact_ticks': 0, 'path_length': sum((float(np.linalg.norm(r['next_pose'][:2] - r['pose'][:2])) for r in rows), 0.)}
    if normal:
        emit('episode_finished', boundary + count, outcome=outcome, metrics=metrics)
    for i in range((count + 31) // 32):
        emit('chunk', boundary + count, path=f'chunks/{i:06d}.npz', sha256='c' * 64,
            episode=0, start=boundary + i * 32, count=min(32, count - i * 32))
    descriptors = {'context': descriptor('authored/context.json', memory.canonical_bytes(context)),
        'job': job, **{k: descriptor('authored/' + k + '.json', b'placeholder') for k in ('raw_manifest', 'raw_events', 'worker_report')}}
    manifest = {'run_id': OWNER, 'controller': 'flynn', 'requested_device': 'cpu', 'teacher_privileged': False,
        'texture': 'checker', 'seed': case['seed'], 'memory_case': case, 'memory_case_sha256': memory.sha256(case),
        'acquisition_protocol_sha256': case['acquisition_protocol_sha256'], 'parent_run_id': SOURCE,
        'parent_event_prefix': application['event_prefix'], 'status': status, 'recording_format': 'palimpsest-npz-v1',
        'recording_max_bytes': 384 * 1024**2, 'recorded_ticks': count, 'final_phase': final_phase,
        'last_outcome': outcome, 'total_tick': boundary + count, 'world_state': post_world,
        'scenario': validate_decision(world.SCENARIO, 'checker', 'flynn', profile_sha256=case['profile_sha256']),
        'recorded_chunks': (count + 31) // 32, 'recorded_events': len(events),
        'metrics': metrics, 'close_reason': 'operator_closed', 'memory_terminal_vnext_context': descriptors['context'],
        'memory_terminal_vnext_context_sha256': memory.sha256(context), 'memory_terminal_vnext_mode': 'memory-terminal-vnext-v1'}
    report = {'schema': 'memory-family-owner-report-v3', 'run_id': OWNER, 'case_id': case['case_id'],
        'operation': 'condition', 'condition': condition, 'status': 'recorded', 'acquired': True,
        'snapshot_sha256': context['source_snapshot']['sha256'], 'source_snapshot_sha256': context['source_snapshot']['sha256'],
        'total_ticks': boundary + count, 'final_phase': final_phase, 'world_state': post_world}
    source_rows = [{'episode': r['episode'], 'tick': r['tick'], **_policy_row(r, SOURCE)[1]} for r in source_projection]
    return rebind({'raw': {'manifest': manifest, 'events': events, 'rows': rows,
        'worker_report': report, 'job': job, 'descriptors': descriptors}, 'context': context,
        'source_application': application, 'source_events': source_events, 'source_rows': source_rows,
        'results': results})


def prove(sample):
    return api().prove_terminal_vnext(sample['raw'], context=sample['context'],
        source_application=sample['source_application'], source_events=sample['source_events'],
        source_rows=sample['source_rows'], deadline=time.monotonic() + 60.)


@pytest.mark.parametrize('condition', CONDITIONS)
@pytest.mark.parametrize('count', (0, 1, 2, 4))
def test_zero_one_two_and_full_prefixes_all_arms(condition, count):
    api()
    sample = fixture(condition, count=count, normal=count == 4)
    result = prove(sample)
    assert result['row_count'] == count
    assert result['first_motor_tick'] == (sample['context']['schedule']['boundary_tick'] if count else None)
    assert result['capped_ticks'] == 900 and result['goal'] is False
    assert result['terminal_sensor_tick'] == (None if count == 4 else sample['context']['schedule']['boundary_tick'] + count)
    assert set(result) == set(api().PROOF_KEYS)
    if not count:
        assert result['last_motor_tick'] is None and result['chunk_count'] == 0 and result['path_length'] == 0.


@pytest.mark.parametrize('kind', ('change', 'null', 'no-event'))
def test_selected_then_exception_replays_local_not_committed_state(kind):
    api()
    sample = fixture(kind=kind, count=1, selected_failure=kind != 'no-event')
    result = prove(sample)
    witness = sample['results'][-1].witness
    assert result['commits'] == []
    assert witness['input_lifecycle']['status'] == 'pending'
    assert witness['local_lifecycle']['status'] == ('pending' if kind == 'no-event' else 'selected')
    assert witness['gold'] == (None if kind == 'no-event' else [] if kind == 'null' else witness['gold'])


def test_world_applied_without_trigger_stays_pending():
    api()
    sample = fixture(count=1)
    result = prove(sample)
    assert result['world_applied'] is True and result['trigger_reached'] is False
    assert sample['results'][-1].witness['local_lifecycle']['status'] == 'pending'


@pytest.mark.parametrize('defect', ('chain', 'local', 'commit', 'ref', 'ref-role', 'pose', 'packet', 'error', 'progress', 'normal', 'source-empty', 'source-hash', 'prefix', 'descriptor', 'policy', 'count', 'context', 'job', 'chunk'))
def test_spoofed_flags_and_witness_hash_chain_do_not_replace_transition_replay(defect):
    api()
    sample = fixture(count=2)
    raw = sample['raw']
    witness = next(e for e in raw['events'] if e['kind'] == 'memory_transition_witness_vnext')['witness']
    if defect == 'chain': witness['previous_sha256'] = '0' * 64
    elif defect == 'local': witness['local_memory_sha256'] = '0' * 64
    elif defect == 'commit': raw['events'].insert(-1, copy.deepcopy(next(e for e in raw['events'] if e['kind'] == 'memory_transition_witness_vnext')))
    elif defect == 'ref': witness['reach']['sensed_event']['sha256'] = '0' * 64
    elif defect == 'ref-role': witness['reach']['cue_event'] = copy.deepcopy(witness['reach']['sensed_event'])
    elif defect == 'pose': raw['rows'][0]['next_pose'][0] += .1
    elif defect == 'packet': next(e for e in raw['events'] if e['kind'] == 'memory_sensed')['packet']['landmarks'] = []
    elif defect == 'error': raw['manifest']['last_outcome']['type'] = 'OSError'
    elif defect == 'progress': raw['events'].append(copy.deepcopy(raw['events'][0]))
    elif defect == 'normal': raw['manifest'].update(status='completed', final_phase='terminated')
    elif defect == 'source-empty': sample['source_rows'] = []
    elif defect == 'source-hash': sample['source_application']['revision'] += 1
    elif defect == 'prefix': sample['source_application']['event_prefix']['sha256'] = '0' * 64
    elif defect == 'descriptor': raw['descriptors']['raw_events']['size_bytes'] += 1
    elif defect == 'policy': raw['rows'][0]['encoded_input'][0] += 1.
    elif defect == 'count': raw['manifest']['recorded_ticks'] = True
    elif defect == 'context': raw['manifest']['memory_terminal_vnext_context_sha256'] = '0' * 64
    elif defect == 'job': raw['job'] = {**raw['job'], 'sha256': '0' * 64}
    elif defect == 'chunk': next(e for e in raw['events'] if e['kind'] == 'chunk')['count'] += 1
    if defect != 'descriptor': rebind(sample)
    with pytest.raises((ValueError, TimeoutError)):
        prove(sample)


def test_every_packet_replays_task1_once_and_inputs_remain_detached():
    api()
    sample = fixture(count=4, normal=True)
    before = copy.deepcopy(sample)
    with patch.object(transition, 'advance_transition_vnext', wraps=transition.advance_transition_vnext) as advance:
        prove(sample)
    assert advance.call_count == 4
    assert memory.sha256(sample['source_application']) == memory.sha256(before['source_application'])
    assert sample['raw']['events'] == before['raw']['events']
    assert all(np.array_equal(a['pose'], b['pose']) for a, b in zip(sample['raw']['rows'], before['raw']['rows']))


def test_normal_malformed_evidence_cannot_fall_back_to_prefix():
    api()
    sample = fixture(count=4, normal=True)
    next(e for e in sample['raw']['events'] if e['kind'] == 'episode_finished')['outcome']['steps'] -= 1
    rebind(sample)
    with pytest.raises(ValueError): prove(sample)


def test_no_public_adapter_or_qualification_shortcut_is_exposed():
    module = api()
    assert not hasattr(module, 'audit_terminal_run_vnext')
    assert not hasattr(module, 'validate_terminal_receipt_vnext')


def test_expired_deadline_refuses_before_transition():
    module = api()
    sample = fixture(count=0)
    with patch.object(transition, 'advance_transition_vnext', wraps=transition.advance_transition_vnext) as advance:
        with pytest.raises(TimeoutError):
            module.prove_terminal_vnext(sample['raw'], context=sample['context'],
                source_application=sample['source_application'], source_events=sample['source_events'],
                source_rows=sample['source_rows'], deadline=time.monotonic() - 1.)
        assert advance.call_count == 0


def test_local_decision_cut_on_raised_terminal_is_reached():
    sample = fixture(count=2)
    assert sample['context']['schedule']['decision_tick'] == sample['context']['schedule']['boundary_tick'] + 2
    assert sample['results'][-1].status == 'raised'
    assert prove(sample)['decision_reached'] is True


def test_returned_supervisor_failure_commits_then_inspects_without_motor():
    sample = fixture('no-U', 'no-event', count=302, supervisor_failure=True)
    result = prove(sample)
    assert result['row_count'] == 302 and result['capped_ticks'] == 900
    assert len(result['witnesses']) == len(result['commits']) == 1
    assert result['decision_reached'] is True
    terminal_tick = result['terminal_sensor_tick']
    terminal = [e['kind'] for e in sample['raw']['events'] if e.get('tick') == terminal_tick and e['kind'] != 'chunk']
    assert terminal[:3] == ['memory_sensed', 'memory_transition_witness_vnext', 'memory_transition_commit_vnext']
    assert terminal[-2:] == ['memory_inspected', 'runtime_failure']
    assert 'memory_cue' not in terminal and 'neural_policy_call' not in terminal


@pytest.mark.parametrize('field', ('run_id', 'memory_case', 'memory_case_sha256', 'seed', 'acquisition_protocol_sha256',
    'controller', 'requested_device', 'teacher_privileged', 'texture', 'scenario', 'recording_format', 'recording_max_bytes',
    'parent_run_id', 'parent_event_prefix', 'memory_terminal_vnext_mode', 'memory_terminal_vnext_context_sha256',
    'memory_terminal_vnext_context', 'recorded_ticks', 'recorded_chunks', 'recorded_events', 'total_tick',
    'world_state', 'status', 'final_phase', 'last_outcome', 'metrics', 'close_reason'))
def test_missing_manifest_projection_field_refuses(field):
    sample = fixture(count=0)
    del sample['raw']['manifest'][field]
    rebind(sample)
    with pytest.raises(ValueError): prove(sample)


@pytest.mark.parametrize('field', ('seed', 'recording_max_bytes', 'recorded_ticks', 'recorded_chunks', 'recorded_events', 'total_tick'))
def test_manifest_bool_cannot_replace_counter(field):
    sample = fixture(count=0)
    sample['raw']['manifest'][field] = False
    rebind(sample)
    with pytest.raises(ValueError): prove(sample)


def test_terminal_packet_fresh_passage_before_decision_refuses():
    sample = fixture(count=1)
    raw, context = sample['raw'], sample['context']
    case = raw['manifest']['memory_case']
    pose = [*case['landmarks'][case['facts'][0]['inspection_landmark_id']], 0.]
    raw['rows'][-1]['next_pose'] = np.asarray(pose, np.float64)
    terminal = next(e for e in raw['events'] if e['kind'] == 'memory_sensed' and e['tick'] == context['schedule']['boundary_tick'] + 1)
    terminal['packet'] = decision.capture_symbolic(*world.reconstruct_inputs(case, pose, terminal['tick'],
        event_tick=context['schedule']['event_tick'], gate_result='closed'), episode_id='episode-0', tick=terminal['tick'])
    assert any(p['passability'] != 'unobserved' for p in terminal['packet']['passages'])
    raw['manifest']['metrics']['path_length'] = float(np.linalg.norm(raw['rows'][-1]['next_pose'][:2] - raw['rows'][-1]['pose'][:2]))
    rebind(sample)
    with pytest.raises(ValueError): prove(sample)


@pytest.mark.parametrize('defect', ('unknown-error', 'missing-witness', 'missing-commit', 'fake-commit-after-raise', 'old-envelope', 'metadata-over', 'rows-over', 'source-rows-over', 'events-over'))
def test_unknown_exception_missing_reached_proof_and_caps_are_unscored(defect):
    sample = fixture(count=2)
    raw = sample['raw']
    if defect == 'unknown-error':
        failure = next(e for e in raw['events'] if e['kind'] == 'runtime_failure')
        failure['error']['type'] = raw['manifest']['last_outcome']['type'] = 'OSError'
        last = [e for e in raw['events'] if e['kind'] == 'memory_transition_witness_vnext'][-1]
        last['witness']['exception']['type'] = 'OSError'
    elif defect == 'missing-witness': raw['events'] = [e for e in raw['events'] if e['kind'] != 'memory_transition_witness_vnext']
    elif defect == 'missing-commit': raw['events'] = [e for e in raw['events'] if e['kind'] != 'memory_transition_commit_vnext']
    elif defect == 'fake-commit-after-raise': raw['events'].append(copy.deepcopy(next(e for e in raw['events'] if e['kind'] == 'memory_transition_commit_vnext')))
    elif defect == 'old-envelope': raw['manifest']['memory_family_oracle_admission_v3'] = {}
    elif defect == 'metadata-over': raw['manifest']['extra_metadata'] = 'x' * (1024**2 + 1)
    elif defect == 'rows-over': raw['rows'] = raw['rows'][:1] * 901
    elif defect == 'source-rows-over': sample['source_rows'] = sample['source_rows'][:1] * 1201
    elif defect == 'events-over': raw['events'] = raw['events'][:1] * 50001
    rebind(sample)
    with pytest.raises(ValueError): prove(sample)


def test_extra_sensor_tail_after_nine_hundred_motor_rows_refuses_before_replay():
    module = api()
    sample = fixture('no-U', 'no-event', count=900, supervisor_failure=True, delayed_route=True)
    with patch.object(module, '_writer', side_effect=AssertionError('semantic preflight must precede writer encoding')), \
            patch.object(transition, 'advance_transition_vnext', wraps=transition.advance_transition_vnext) as advance:
        with pytest.raises(ValueError, match='postterminal sensor tail'):
            prove(sample)
        assert advance.call_count == 0


def test_oversized_nine_hundred_row_normal_trace_is_resource_refusal_not_scored(tmp_path):
    sample = fixture('no-U', 'no-event', count=900, normal=True, delayed_route=True)
    assert sample['raw']['manifest']['last_outcome']['reason'] == 'time_limit'
    assert sample['raw']['descriptors']['raw_events']['size_bytes'] > 5 * 1024**2
    (tmp_path / 'authored-normal-900-descriptor.json').write_bytes(memory.canonical_bytes({
        'case_id': sample['context']['case_id'], 'condition': 'no-U', 'kind': 'no-event',
        'motor_rows': 900, 'terminal_kind': 'row-backed-time_limit',
        'event_count': len(sample['raw']['events']), 'event_limit_bytes': 5 * 1024**2,
        'raw_events': sample['raw']['descriptors']['raw_events']}))
    with pytest.raises(ValueError, match='descriptor byte size'):
        prove(sample)


def test_nonempty_source_snapshot_identity_is_required_even_for_zero_condition():
    sample = fixture(count=0, empty_snapshot=True)
    with pytest.raises(ValueError, match='nonempty source snapshot'):
        prove(sample)


def test_decoded_rows_cannot_execute_an_opaque_array_loader():
    sample = fixture(count=1)
    calls = []
    class OpaqueArray:
        def __array__(self, dtype=None):
            calls.append('executed')
            return np.array([0., 0., 0.], np.float64)
    sample['raw']['rows'][0]['pose'] = OpaqueArray()
    with pytest.raises((ValueError, TypeError)):
        prove(sample)
    assert calls == []


def test_actual_authored_runwriter_readback_preserves_safe_numpy_scalar_rows(tmp_path):
    from palimpsest.records import RunWriter, iter_ticks
    sample = fixture(count=1)
    original = sample['raw']['rows'][0]
    writer = RunWriter(tmp_path / 'recording', {'run_id': OWNER}, max_bytes=384 * 1024**2)
    writer.tick(0, original['tick'], **{k: v for k, v in original.items() if k not in ('episode', 'tick')})
    writer.finish({}, status='completed')
    decoded = list(iter_ticks(writer.path))[0]
    assert type(decoded['reward']) is np.float64 and type(decoded['revision']) is np.int64
    sample['raw']['rows'] = [decoded]
    source_writer = RunWriter(tmp_path / 'source-recording', {'run_id': SOURCE}, max_bytes=512 * 1024**2)
    for row in sample['source_rows']:
        source_writer.tick(0, row['tick'], **{k: v for k, v in row.items() if k not in ('episode', 'tick')})
    source_writer.finish({}, status='completed')
    sample['source_rows'] = list(iter_ticks(source_writer.path))
    result = prove(sample)
    assert result['row_count'] == 1
    from scripts import memory_family_raw_audit_v4 as raw_audit
    assert result['row_sequence_sha256'] == raw_audit._audit_rows([decoded], 'condition')[2]


@pytest.mark.parametrize('over', (0, 1))
def test_round1_complete_source_event_bytes_bound_valid_prefix_and_suffix(over):
    sample = fixture(count=0)
    source_events = sample['source_events']
    prefix = copy.deepcopy(sample['source_application']['event_prefix'])
    suffix = {'sequence': len(source_events), 'kind': 'diagnostic', 'run_id': SOURCE,
        'episode': 0, 'episode_step': sample['context']['schedule']['boundary_tick'],
        'tick': sample['context']['schedule']['boundary_tick'], 'message': ''}
    limit = 7 * 1024**2
    before = sum(len(encoded(e)) for e in source_events)
    suffix['message'] = 'x' * (limit + over - before - len(encoded(suffix)))
    source_events.append(suffix)
    assert sum(len(encoded(e)) for e in source_events) == limit + over
    assert sample['source_application']['event_prefix'] == prefix
    if over:
        from scripts import memory_family_oracle_v3 as oracle
        with patch.object(oracle, '_source_evidence', side_effect=AssertionError('source replay must follow whole-stream cap')):
            with pytest.raises(ValueError, match='source event byte ceiling'):
                prove(sample)
    else:
        assert prove(sample)['row_count'] == 0


@pytest.mark.parametrize('group,field', (('outcome', 'episode'), ('outcome', 'steps'),
    ('outcome', 'final_distance'), ('metrics', 'reward'), ('metrics', 'contact_ticks'), ('metrics', 'path_length')))
def test_round1_normal_event_only_numeric_aliases_refuse(group, field):
    sample = fixture(count=4, normal=True)
    manifest = copy.deepcopy(sample['raw']['manifest'])
    event = next(e for e in sample['raw']['events'] if e['kind'] == 'episode_finished')
    event['outcome'] = copy.deepcopy(event['outcome'])
    event['metrics'] = copy.deepcopy(event['metrics'])
    original = event[group][field]
    event[group][field] = False if field in ('episode', 'contact_ticks') else float(original) if field == 'steps' else int(original)
    assert event[group] == (manifest['last_outcome'] if group == 'outcome' else manifest['metrics'])
    assert memory.canonical_bytes(event[group]) != memory.canonical_bytes(manifest['last_outcome'] if group == 'outcome' else manifest['metrics'])
    assert sample['raw']['manifest'] == manifest
    rebind(sample)
    with pytest.raises(ValueError):
        prove(sample)


@pytest.mark.parametrize('flag', (1, 1.0))
def test_round1_hash_bound_source_eye_numeric_aliases_refuse(flag):
    original_application = _application
    def inexact_application(*args, **kwargs):
        application = original_application(*args, **kwargs)
        application['eyes'] = {'left': flag, 'right': flag}
        return application
    with patch(__name__ + '._application', side_effect=inexact_application):
        sample = fixture(count=0)
    restored = next(e for e in sample['raw']['events'] if e['kind'] == 'application_restored')
    restored['eyes'] = {'left': True, 'right': True}
    assert sample['context']['source_application_sha256'] == memory.sha256(sample['source_application'])
    assert type(sample['source_application']['eyes']['left']) is type(flag)
    rebind(sample)
    with pytest.raises(ValueError):
        prove(sample)
