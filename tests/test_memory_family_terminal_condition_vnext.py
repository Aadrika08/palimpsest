"""Conditional pair tests: authored values and 6a.1 files; no actual authority."""
import copy
import importlib
import math
import time
from unittest.mock import patch

import numpy as np
import pytest

from palimpsest import memory, memory_decision as decision, memory_decision_world as world
from palimpsest import memory_experiment, memory_transition_vnext as transition
from palimpsest.profiles import validate_decision
from scripts import memory_family_terminal_audit_vnext as audit
from test_memory_family_terminal_audit_vnext import descriptor, rebind, fixture as generic_source, prove
from test_memory_family_oracle_v3 import _event, _world_record
from test_memory_family_raw_audit_v4 import _policy_row
import test_memory_family_source_consumer_vnext as authored_source

SOURCE = authored_source.SOURCE
OWNER = authored_source.RUN
CONDITIONS = memory_experiment.CONDITIONS


def api():
    try:
        return importlib.import_module('scripts.memory_family_terminal_condition_vnext')
    except ModuleNotFoundError:
        pytest.fail('Task5a registered conditional pair API is missing', pytrace=False)


def histories():
    result = {}
    for role, seed, relation in (('own', 200, 'local_cue'), ('swapped', 1200, 'paired_cue')):
        e = memory_experiment.make_history(seed, relation)
        bundle = {'e': e, 'u': memory.fit(e), 'history_sha256': memory.sha256(e)}
        result[role] = {'descriptor': descriptor('histories/' + role + '.json', memory.canonical_bytes(bundle)), 'bundle': bundle}
    return result


def resources(q, context, h):
    empty = memory.artifact(method='empty-v1')
    u = h['own']['bundle']['u'] if q in ('own', 'sham') else h['swapped']['bundle']['u'] if q == 'swapped' else memory.artifact('local_cue') if q == 'hand-authored' else empty
    resource = h['own']['bundle']['e'] if q == 'retrieval' else [] if q == 'oracle' else None
    provenance = h['own']['descriptor']['sha256'] if q in ('own', 'sham', 'retrieval') else h['swapped']['descriptor']['sha256'] if q == 'swapped' else transition.pending_provenance_vnext(context) if q == 'oracle' else memory_experiment.PROTOCOL_SHA256
    return {'selector': {'version': 1, 'condition': q, 'limit': 1, 'resource': resource,
        'resource_sha256': memory.sha256(resource), 'provenance_sha256': provenance}, 'u': u}


def condition_evidence(base, h, condition='oracle', count=2, *, normal=False,
        selected_failure=False):
    # Condition-only adaptation of Task3a's real pure worker/persistence fixture.
    # Source values are supplied intact; every W/C is newly produced below.
    application = copy.deepcopy(base['source_application'])
    source_events, source_rows = copy.deepcopy(base['source_events']), copy.deepcopy(base['source_rows'])
    context = copy.deepcopy(base['context'])
    context['condition'] = condition
    case, source, source_world = application['world_task_state']['case'], application['memory'], application['world_task_state']
    kind, boundary = case['kind'], application['episode_step']
    pose = source_rows[-1]['next_pose'].tolist()
    values = copy.deepcopy(resources(condition, context, h))
    config, u = values['selector'], values['u']
    context['condition_resources_sha256'] = memory.sha256(values)
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
        emit('memory_cue', tick, bearing=result.bearing, raw_upstream_bearing=[1., 0.])
        next_pose = pose.copy()
        if not normal and offset == count - 1:
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
        assert results[-1].status == 'raised', 'authored natural terminal must actually terminate'
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
    return rebind({'raw': {'manifest': manifest, 'events': events, 'rows': rows,
        'worker_report': report, 'job': job, 'descriptors': descriptors}, 'context': context,
        'source_application': application, 'source_events': source_events, 'source_rows': source_rows,
        'results': results})


def source_value(sample, h):
    return {'application': sample['source_application'], 'events': sample['source_events'],
        'rows': sample['source_rows'], 'histories': h}


def pair(sample, h, proof=None, deadline=None):
    return api().prove_pair_vnext(source_value(sample, h), sample['raw'], context=sample['context'],
        terminal_proof=prove(sample) if proof is None else proof,
        deadline=time.monotonic()+60 if deadline is None else deadline)


@pytest.fixture(scope='module')
def base():
    return generic_source(count=2)


@pytest.mark.parametrize('q', CONDITIONS)
def test_all_nine_registered_mappings_replay_whole_proof(base, q):
    api()
    h = histories()
    sample = condition_evidence(base, h, q)
    proof = prove(sample)
    result = pair(sample, h, proof)
    assert set(result) == {'schema', 'context_sha256', 'terminal_proof_sha256', 'history_bundles', 'endpoint'}
    assert result['schema'] == 'memory-terminal-pair-pure-vnext-v1'
    assert result['context_sha256'] == memory.sha256(sample['context'])
    assert result['terminal_proof_sha256'] == memory.sha256(proof)
    assert result['history_bundles'] == {k: v['descriptor'] for k, v in h.items()}
    assert type(result['endpoint']['path_length']) is float
    assert result['endpoint'] == {k: proof['row_count' if k == 'continuation_ticks' else k]
        for k in ('terminal_sensor_tick', 'goal', 'continuation_ticks', 'capped_ticks', 'path_length', 'outcome', 'trace_digest', 'invariant')}


@pytest.mark.parametrize('q', CONDITIONS)
@pytest.mark.parametrize('defect', ('u', 'provenance', 'limit', 'resource-hash', 'resource'))
def test_rebound_invalid_mapping_is_rejected_before_replay(base, q, defect):
    api()
    h = histories()
    sample = condition_evidence(base, h, q)
    proof = prove(sample)
    event = next(e for e in sample['raw']['events'] if e['kind'] == 'memory_selector_configured')
    if defect == 'u': event['u'] = memory.artifact('paired_cue')
    elif defect == 'provenance': event['selector']['provenance_sha256'] = '0'*64
    elif defect == 'limit': event['selector']['limit'] = 0
    elif defect == 'resource-hash': event['selector']['resource_sha256'] = '0'*64
    else:
        event['selector']['resource'] = h['swapped']['bundle']['e'] if q == 'retrieval' else ['wrong'] if q == 'oracle' else []
        event['selector']['resource_sha256'] = memory.sha256(event['selector']['resource'])
    sample['context']['condition_resources_sha256'] = memory.sha256({'selector': event['selector'], 'u': event['u']})
    sample['raw']['manifest']['memory_terminal_vnext_context_sha256'] = memory.sha256(sample['context'])
    rebind(sample)
    sample['raw']['manifest']['memory_terminal_vnext_context'] = copy.deepcopy(sample['raw']['descriptors']['context'])
    rebind(sample)
    with patch.object(audit, 'prove_terminal_vnext', side_effect=AssertionError('mapping did not refuse')):
        with pytest.raises(ValueError, match='mapping'):
            pair(sample, h, proof=proof)


@pytest.mark.parametrize('defect', ('refit', 'history-hash', 'descriptor-hash', 'descriptor-size', 'alias', 'overlap', 'role'))
def test_history_values_and_physical_bytes_are_premises_checked_independently(base, defect):
    api()
    h = histories()
    sample = condition_evidence(base, h, 'own')
    proof = prove(sample)
    if defect == 'refit': h['own']['bundle']['u'] = memory.artifact('local_cue')
    elif defect == 'history-hash': h['own']['bundle']['history_sha256'] = '0'*64
    elif defect == 'descriptor-hash': h['own']['descriptor']['sha256'] = '0'*64
    elif defect == 'descriptor-size': h['own']['descriptor']['size_bytes'] += 1
    elif defect == 'alias': h['swapped']['descriptor']['path'] = h['own']['descriptor']['path']
    elif defect == 'overlap': h['swapped']['bundle'] = copy.deepcopy(h['own']['bundle'])
    else: h['own'], h['swapped'] = h['swapped'], h['own']
    if defect in ('refit', 'history-hash', 'overlap'):
        for item in h.values(): item['descriptor'] = descriptor(item['descriptor']['path'], memory.canonical_bytes(item['bundle']))
    with pytest.raises(ValueError): pair(sample, h, proof=proof)


@pytest.mark.parametrize('field', sorted(audit.PROOF_KEYS))
def test_every_forged_proof_field_is_compared_to_fresh_replay(base, field):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    proof[field] = None if proof[field] is not None else 'forged'
    with pytest.raises(ValueError): pair(sample, h, proof)


@pytest.mark.parametrize('count,selected,kind', ((1,False,'change'), (2,False,'change'), (1,True,'change'), (1,True,'null'), (2,False,'no-event')))
def test_natural_short_reached_gold_and_no_event_pending(count, selected, kind):
    api()
    h = histories()
    sample = condition_evidence(generic_source(kind=kind), h, count=count, selected_failure=selected)
    proof = prove(sample)
    result = pair(sample, h, proof)
    assert result['endpoint']['continuation_ticks'] == count
    assert result['endpoint']['capped_ticks'] == 900
    assert result['endpoint']['terminal_sensor_tick'] == sample['context']['schedule']['boundary_tick'] + count
    if selected:
        witness = sample['results'][-1].witness
        assert witness['local_lifecycle']['status'] == 'selected' and not proof['commits']
        assert witness['gold'] == ([] if kind == 'null' else witness['gold'])
        if kind == 'change': assert witness['gold']
    if kind == 'no-event':
        assert proof['trigger_reached'] is False and proof['world_applied'] is False
        assert all(r.witness is None or r.witness['local_lifecycle']['status'] == 'pending' for r in sample['results'])


@pytest.mark.parametrize('zero', (False, True))
def test_real_authored_fd_source_frozen_resources_and_new_condition(zero):
    api()
    h = histories()
    q = 'oracle' if zero else 'own'
    def admission_edit(role, value):
        if role == 'admission':
            c = value['condition_slot']
            if q == 'own': c['resources'] = resources(q, {}, h)
            else: c['resources']['u'] = memory.artifact(method='empty-v1')
            c['condition_resources_sha256'] = memory.sha256(c['resources'])
    original_acquire = authored_source._acquire
    def acquire(case):
        values = original_acquire(case)
        if zero: values[-1][-1]['next_pose'] = [6., 6., 0.]
        return values
    # This changes newly authored source geometry BEFORE raw/numeric/events/SNP
    # are written, never a live held source or downstream hash relabel.
    with patch.object(authored_source, '_acquire', acquire):
        fixture = authored_source.authored(condition=q, edit=admission_edit)
    entered = False
    with authored_source.lease(fixture) as held:
        entered = True
        held.recheck()
        base = {'context': held.context, 'source_application': held.source_application,
            'source_events': held._source_events, 'source_rows': held._source_rows}
        sample = condition_evidence(base, h, q, count=0 if zero else 2)
        assert sample['context'] == held.context
        before = snapshot_inputs(sample, h)
        result = pair(sample, h)
        assert snapshot_inputs(sample, h) == before
        held.recheck()
        assert result['endpoint']['continuation_ticks'] == (0 if zero else 2)
        if zero:
            assert result['endpoint']['terminal_sensor_tick'] == held.context['schedule']['boundary_tick']
            assert result['endpoint']['path_length'] == 0. and result['endpoint']['goal'] is False
            assert result['endpoint']['capped_ticks'] == 900
    assert entered


def snapshot_inputs(sample, h):
    # state_digest includes dtype/shape/array bytes and NumPy scalar values.
    from palimpsest import snapshots
    return snapshots.state_digest({'sample': sample_without_results(sample), 'histories': h})


def sample_without_results(sample):
    return {k: v for k, v in sample.items() if k != 'results'}


@pytest.mark.parametrize('defect', ('application', 'm', 'world', 'normal-relabel', 'retained', 'source-view'))
def test_source_bindings_and_terminal_relabels_still_reach_task3a(base, defect):
    api()
    h = histories()
    sample = condition_evidence(base, h, 'own')
    proof = prove(sample)
    if defect in ('application', 'm', 'world'):
        key = {'application':'source_application_sha256', 'm':'source_m_sha256', 'world':'source_world_sha256'}[defect]
        sample['context'][key] = '0'*64
    elif defect == 'normal-relabel': sample['raw']['manifest'].update(status='completed', final_phase='terminated')
    elif defect == 'retained': next(e for e in sample['raw']['events'] if e['kind']=='memory_selector_configured')['retained_memory_sha256'] = '0'*64
    else: sample['source_application']['memory']['selector']['provenance_sha256'] = '0'*64
    sample['raw']['manifest']['memory_terminal_vnext_context_sha256'] = memory.sha256(sample['context'])
    rebind(sample)
    sample['raw']['manifest']['memory_terminal_vnext_context'] = copy.deepcopy(sample['raw']['descriptors']['context'])
    rebind(sample)
    with patch.object(audit, 'prove_terminal_vnext', wraps=audit.prove_terminal_vnext) as replay, patch.object(audit, '_source', wraps=audit._source) as source_check:
        with pytest.raises(ValueError): pair(sample, h, proof)
        assert replay.call_count == 1
        assert source_check.call_count == 1


@pytest.mark.parametrize('deadline', (True, float('nan'), float('inf'), -1.))
def test_invalid_or_expired_deadline(base, deadline):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    with pytest.raises((ValueError, TimeoutError)): pair(sample, h, proof={}, deadline=deadline)


def test_result_detached_and_all_inputs_unchanged(base):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    before = snapshot_inputs(sample, h), memory.canonical_bytes(proof)
    result = pair(sample, h, proof)
    result['history_bundles']['own']['path'] = 'changed'
    result['endpoint']['outcome']['reason'] = 'changed'
    assert (snapshot_inputs(sample, h), memory.canonical_bytes(proof)) == before


@pytest.mark.parametrize('q', CONDITIONS)
def test_even_unused_histories_require_independent_e_only_refit(base, q):
    api()
    h = histories()
    sample = condition_evidence(base, h, q)
    proof = prove(sample)
    h['swapped']['bundle']['u'] = memory.artifact('paired_cue')
    item = h['swapped']
    item['descriptor'] = descriptor(item['descriptor']['path'], memory.canonical_bytes(item['bundle']))
    with patch.object(audit, 'prove_terminal_vnext', side_effect=AssertionError('refit did not refuse')):
        with pytest.raises(ValueError, match='differs'): pair(sample, h, proof)


@pytest.mark.parametrize('part', ('source', 'application', 'histories', 'history', 'bundle', 'descriptor', 'condition', 'descriptors', 'context', 'proof'))
@pytest.mark.parametrize('extra', (False, True))
def test_exact_outer_key_sets(base, part, extra):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    source = source_value(sample, h)
    values = {'source': source, 'application': source['application'], 'histories': h,
        'history': h['own'], 'bundle': h['own']['bundle'], 'descriptor': h['own']['descriptor'],
        'condition': sample['raw'], 'descriptors': sample['raw']['descriptors'],
        'context': sample['context'], 'proof': proof}
    target = values[part]
    if extra: target['unknown'] = None
    else: target.pop(next(iter(target)))
    with pytest.raises(ValueError):
        api().prove_pair_vnext(source, sample['raw'], context=sample['context'], terminal_proof=proof,
            deadline=time.monotonic()+60)


def test_no_event_ordinary_decision_does_not_require_oracle_resolution():
    api()
    h = histories()
    base = generic_source(kind='no-event')
    with patch.object(memory_experiment, 'selection_for_condition', side_effect=AssertionError('unreached selector invoked')), patch.object(transition, 'resolve_gold_vnext', side_effect=AssertionError('unreached oracle resolved')):
        sample = condition_evidence(base, h, count=4, normal=True)
        proof = prove(sample)
        result = pair(sample, h, proof)
    assert proof['decision_reached'] is True
    assert proof['trigger_reached'] is False and proof['world_applied'] is False
    assert result['endpoint']['terminal_sensor_tick'] is None
    for result in sample['results']:
        if result.witness is not None:
            assert result.witness['stages'] == []
            assert result.witness['gold'] is None and result.witness['selection'] is None


def test_deadline_rechecked_after_replay_and_pair_does_no_io(base):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    original = audit.prove_terminal_vnext
    expired = False
    def replay(*args, **kwargs):
        nonlocal expired
        result = original(*args, **kwargs)
        expired = True
        return result
    real_deadline = audit._deadline
    def clock(deadline):
        if expired: raise TimeoutError('Terminal proof deadline exhausted')
        return real_deadline(deadline)
    with patch('builtins.open', side_effect=AssertionError('pair attempted file I/O')):
        pair(sample, h, proof)
        with patch.object(audit, 'prove_terminal_vnext', replay), patch.object(audit, '_deadline', clock):
            with pytest.raises(TimeoutError, match='deadline'): pair(sample, h, proof)


@pytest.mark.parametrize('field', ('version', 'limit'))
def test_bool_selector_counter_is_not_an_integer(base, field):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    event = next(e for e in sample['raw']['events'] if e['kind']=='memory_selector_configured')
    event['selector'][field] = True
    sample['context']['condition_resources_sha256'] = memory.sha256({'selector': event['selector'], 'u': event['u']})
    rebind(sample)
    with pytest.raises(ValueError, match='mapping'): pair(sample, h, proof)


@pytest.mark.parametrize('side', ('source', 'condition'))
def test_opaque_arrays_are_rejected_without_conversion(base, side):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    class Proxy:
        def __array__(self):
            raise AssertionError('opaque array hook invoked')
    rows = sample['source_rows'] if side == 'source' else sample['raw']['rows']
    rows[0]['action'] = Proxy()
    with pytest.raises(ValueError, match='plain NumPy'): pair(sample, h, proof)


def test_original_raw_fields_forwarded_unchanged_to_independent_replay(base):
    api()
    h = histories()
    sample = condition_evidence(base, h)
    proof = prove(sample)
    with patch.object(audit, 'prove_terminal_vnext', wraps=audit.prove_terminal_vnext) as replay:
        pair(sample, h, proof)
    assert replay.call_count == 1
    args, kwargs = replay.call_args
    assert args[0] is sample['raw']
    assert kwargs['source_application'] is sample['source_application']
    assert kwargs['source_events'] is sample['source_events']
    assert kwargs['source_rows'] is sample['source_rows']


@pytest.mark.parametrize('q', CONDITIONS)
@pytest.mark.parametrize('field', ('row_count', 'trigger_reached'))
def test_forged_endpoint_or_reached_flag_rejected_in_every_slot(base, q, field):
    api()
    h = histories()
    sample = condition_evidence(base, h, q)
    proof = prove(sample)
    proof[field] = proof[field] + 1 if field == 'row_count' else not proof[field]
    with patch.object(audit, 'prove_terminal_vnext', wraps=audit.prove_terminal_vnext) as replay:
        with pytest.raises(ValueError, match='Fresh complete'): pair(sample, h, proof)
        assert replay.call_count == 1
