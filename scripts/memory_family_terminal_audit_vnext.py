"""Conditional pure terminal replay, Task3a only; no public admission adapter.

Supplied decoded source/application/rows are premises, not authenticated SNP or
native placement. Descriptors bind the specified deterministic representations;
they do not prove physical originals used them. Job-body correspondence, actual
source authority, NPZ container identity/inventory, held custody and publication
remain Task3b obligations. This function opens no files and grants no authority.
"""
import copy
import hashlib
import json
import math
import time

import numpy as np

from palimpsest import memory, memory_decision as decision, memory_decision_world as world
from palimpsest import memory_transition_vnext as transition, snapshots
from palimpsest.profiles import validate_decision
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_oracle_admission_v3 as admission
from scripts import memory_family_oracle_v3 as oracle
from scripts import memory_family_raw_audit_v4 as legacy


PROOF_KEYS = frozenset(('schema context job raw_manifest raw_events worker_report source_snapshot '
    'boundary_tick terminal_sensor_tick first_motor_tick last_motor_tick row_count chunk_count '
    'world_applied trigger_reached decision_reached witnesses commits outcome goal path_length '
    'capped_ticks trace_digest row_sequence_sha256 camera_sequence_sha256 invariant').split())
_RAW_KEYS = frozenset(('manifest events rows worker_report job descriptors').split())
_DESCRIPTORS = frozenset(('context job raw_manifest raw_events worker_report').split())
_ENVELOPE = frozenset(('sequence kind run_id episode episode_step tick').split())
_MIB = 1024**2
_SCALAR_TYPES = {'reward': np.float64, 'simulation_time': np.float64,
    'revision': np.int64, 'latency': np.float64, 'step_latency': np.float64}


def _fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('Missing or unknown terminal evidence fields')


def _require(predicate, message):
    if not predicate:
        raise ValueError(message)


def _int(value, maximum=2100):
    _require(type(value) is int and 0 <= value <= maximum, 'Invalid exact integer counter')
    return value


def _same(left, right):
    _require(memory.canonical_bytes(left) == memory.canonical_bytes(right), 'Terminal evidence differs')


def _deadline(deadline):
    _require(type(deadline) in (int, float) and math.isfinite(deadline), 'Invalid terminal proof deadline')
    if time.monotonic() >= deadline:
        raise TimeoutError('Terminal proof deadline exhausted')


def _writer(value):
    # Exactly records._json, including ensure_ascii=True, plus its real newline.
    memory.canonical_bytes(value)  # Also rejects excessive nesting/nonfinite input.
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def _descriptor(value, payload, maximum):
    transition.validate_descriptor_vnext(value, max_bytes=maximum)
    _require(value['size_bytes'] == len(payload) and value['sha256'] == hashlib.sha256(payload).hexdigest(),
        'Descriptor differs from specified deterministic bytes')


def _events(events, run_id):
    _require(type(events) is list and 0 < len(events) <= 50000, 'Invalid event count')
    for sequence, event in enumerate(events):
        _require(type(event) is dict and type(event.get('kind')) is str, 'Invalid event')
        _require(type(event.get('sequence')) is int and event['sequence'] == sequence, 'Nonconsecutive event sequence')
        if event['kind'] == 'chunk':
            _require(event.get('run_id') in (None, run_id), 'Chunk belongs to another run')
        else:
            _require(event.get('run_id') == run_id, 'Event belongs to another run')
            for name in ('episode', 'tick', 'episode_step'):
                _int(event.get(name))
            _require(event['episode'] == 0 and event['tick'] == event['episode_step'], 'Wrong event boundary')
        _require(event['kind'] not in legacy.FORBIDDEN_EVENTS | {
            'transfer_driver_input', 'source_preparation_input'}, 'Forbidden replacement or privileged input')
        if event['kind'] == 'command_received':
            _require(event.get('command', {}).get('kind') == 'step', 'Undeclared condition command')


def _decoded_rows(rows, maximum_rows, maximum_bytes):
    _require(type(rows) is list and len(rows) <= maximum_rows, 'Decoded rows exceed count bound')
    known_bytes = 0
    for row in rows:
        _fields(row, compact.RAW_FIELDS)
        for name in compact.RAW_FIELDS - {'episode', 'tick'}:
            # iter_ticks returns arrays for shaped fields and exact NumPy scalars
            # for scalar fields. Preserve both representations/digest semantics;
            # never invoke an opaque __array__ hook or accept an array subclass.
            _require(type(row[name]) is np.ndarray or type(row[name]) is _SCALAR_TYPES.get(name),
                'Decoded row requires plain NumPy arrays or exact safe scalar types')
            known_bytes += row[name].nbytes
            _require(known_bytes <= maximum_bytes, 'Decoded array bytes alone exceed raw ceiling')
    # This is only a necessary lower-bound refusal, not NPZ/container accounting.


def _source(application, events, rows, context):
    _fields(application, oracle.APPLICATION_FIELDS)
    _same(application['eyes'], {'left': True, 'right': True})
    _require(type(rows) is list and 0 < len(rows) <= 1200, 'Source must remain nonempty and bounded')
    _require(context['source_snapshot']['size_bytes'] > 0, 'A nonempty source snapshot identity is required')
    _decoded_rows(rows, 1200, 512 * _MIB)
    case = world.validate_case(application['world_task_state']['case'])
    _require(case['version'] == 3, 'Source requires original family case3')
    _same(case['case_id'], context['case_id']); _same(case['kind'], context['kind'])
    _same(memory.sha256(case), context['case_sha256'])
    source_world = world.validate_state(application['world_task_state'])
    b = _int(application['episode_step'])
    _require(b > 0 and b == context['schedule']['boundary_tick'], 'Wrong acquired boundary')
    # Compatible narrow old validator only; its report argument supplies data,
    # not a receipt or qualification. UUID validation belongs to Context here.
    _, state, _, _ = legacy._source_application(application, case, context['source_run_id'],
        {'total_ticks': b, 'world_state': source_world})
    for name in ('schema_version', 'episode', 'total_tick', 'revision', 'seed'):
        _int(application[name], maximum=2**63 - 1)
    _require(application['schema_version'] == 8 and application['episode'] == 0, 'Wrong source application version/episode')
    _same(application['teacher_reset_identity'], None); _same(application['task_state'], None)
    _same(application['manual_action'], [0., 0.])
    _fields(application['controller_tensors'], ('graph_buffers', 'parameters'))
    for value in application['controller_tensors'].values(): memory._digest(value)
    _metrics(application['metrics'])
    _require(type(application['original_commands']) is dict and type(application['receipts']) is dict
        and set(application['original_commands']) == set(application['receipts']), 'Invalid source receipt bank')
    _require(not application['pending_commands'], 'Source has pending commands')
    _same(state['graph'], world.public_graph(case))
    _same(state['initial_m'], {'version': 1, 'facts': case['facts']})
    _same(state['e'], {'version': 1, 'episodes': []})
    _same(state['u'], memory.artifact(method='empty-v1'))
    _same(state['selector'], {'version': 1, 'condition': 'no-U', 'limit': 1, 'resource': None,
        'resource_sha256': memory.sha256(None), 'provenance_sha256': case['profile_sha256']})
    _same(context['source_application_sha256'], memory.sha256(application))
    _same(context['source_m_sha256'], memory.sha256(state['m']))
    _same(context['source_world_sha256'], memory.sha256(source_world))
    _same(context['source_invariant_sha256'], transition.terminal_condition_invariant_vnext(application))
    _events(events, context['source_run_id'])
    prefix = application['event_prefix']; _fields(prefix, ('sha256', 'size_bytes', 'event_count'))
    _int(prefix['event_count'], 50000); _int(prefix['size_bytes'], 7 * _MIB)
    memory._digest(prefix['sha256'])
    count = prefix['event_count']
    _require(0 < count <= len(events), 'Invalid source event prefix count')
    total_bytes, prefix_bytes, prefix_digest = 0, 0, hashlib.sha256()
    for index, event in enumerate(events):
        payload = _writer(event)
        total_bytes += len(payload)
        _require(total_bytes <= 7 * _MIB, 'Supplied source event byte ceiling exceeded')
        if index < count:
            prefix_bytes += len(payload)
            prefix_digest.update(payload)
    _require(prefix_bytes == prefix['size_bytes'] and prefix_digest.hexdigest() == prefix['sha256'],
        'Source event prefix commitment differs')
    acquired_index, _ = oracle._single(events, 'memory_acquired_boundary', 'source')
    _require(acquired_index < count, 'Source prefix precedes its acquired cut')
    projection, _, _ = legacy._audit_rows(rows, 'source')
    _require(len(projection) == b, 'Source rows do not reach acquired boundary')
    oracle._source_evidence(case, application, events, projection)
    return case, state, source_world, projection


def _metrics(value):
    _fields(value, ('reward', 'contact_ticks', 'path_length'))
    for name in ('reward', 'path_length'):
        _require(type(value[name]) is float and math.isfinite(value[name]), 'Invalid finite metric')
    _int(value['contact_ticks'], 2**63 - 1)
    _require(value['path_length'] >= 0., 'Negative path length')


def _manifest(raw, context, application, case):
    m, report, events, rows = (raw[name] for name in ('manifest', 'worker_report', 'events', 'rows'))
    _require(type(m) is dict and type(rows) is list and len(rows) <= 900, 'Invalid bounded condition rows/manifest')
    b, n = context['schedule']['boundary_tick'], len(rows)
    expected = {'run_id': context['run_id'], 'memory_case': case, 'memory_case_sha256': context['case_sha256'],
        'seed': case['seed'], 'acquisition_protocol_sha256': case['acquisition_protocol_sha256'],
        'controller': 'flynn', 'requested_device': 'cpu', 'teacher_privileged': False, 'texture': 'checker',
        'scenario': validate_decision(world.SCENARIO, 'checker', 'flynn', profile_sha256=case['profile_sha256']),
        'recording_format': 'palimpsest-npz-v1', 'recording_max_bytes': 384 * _MIB,
        'parent_run_id': context['source_run_id'], 'parent_event_prefix': application['event_prefix'],
        'memory_terminal_vnext_mode': 'memory-terminal-vnext-v1',
        'memory_terminal_vnext_context_sha256': memory.sha256(context),
        'memory_terminal_vnext_context': raw['descriptors']['context'], 'close_reason': 'operator_closed',
        'recorded_ticks': n, 'recorded_events': len(events), 'recorded_chunks': (n + 31) // 32,
        'total_tick': b + n}
    for name, value in expected.items():
        _require(name in m, 'Missing required manifest field: ' + name)
        _same(m[name], value)
    _require('memory_family_oracle_admission_v3' not in m, 'Old admission envelope cannot authorize successor')
    for name in ('seed', 'recording_max_bytes', 'recorded_ticks', 'recorded_events', 'recorded_chunks', 'total_tick'):
        _int(m[name], 2**63 - 1)
    _fields(report, admission.REPORT_FIELDS)
    expected_report = {'schema': admission.REPORT_SCHEMA, 'run_id': context['run_id'],
        'case_id': context['case_id'], 'operation': 'condition', 'condition': context['condition'],
        'status': 'recorded', 'acquired': True, 'snapshot_sha256': context['source_snapshot']['sha256'],
        'source_snapshot_sha256': context['source_snapshot']['sha256'], 'total_ticks': b + n,
        'final_phase': m.get('final_phase'), 'world_state': m.get('world_state')}
    _same(report, expected_report)
    _int(report['total_ticks'])
    _require(m.get('final_phase') in ('failed', 'terminated', 'truncated'), 'No paused or incomplete prefix admission')
    _same(m.get('status'), 'failed' if m['final_phase'] == 'failed' else 'completed')
    _require('last_outcome' in m and type(m['last_outcome']) is dict, 'Missing exact terminal outcome')
    _metrics(m.get('metrics'))
    return b, n, world.validate_state(m['world_state'])


def _chunks(events, b, n):
    chunks = [e for e in events if e['kind'] == 'chunk']
    _require(len(chunks) == (n + 31) // 32 <= 29, 'Wrong chunk count')
    for index, event in enumerate(chunks):
        for name in ('episode', 'start', 'count'): _int(event.get(name))
        _require(event['episode'] == 0 and event['start'] == b + index * 32
            and event['count'] == min(32, n - index * 32) > 0
            and event.get('path') == f'chunks/{index:06d}.npz', 'Wrong chunk sequence or coverage')
        memory._digest(event.get('sha256'))
    return chunks


def _policy(rows, events):
    calls = legacy._policy_calls(events)
    _require([e['tick'] for e in calls] == [r['tick'] for r in rows], 'Policy calls differ from all motor rows')
    for row, event in zip(rows, calls):
        _same(event['result_sha256'], {k: snapshots.state_digest(row[k]) for k in ('action', 'encoded_input', 'raw_output')})
        _same(event['cameras_sha256'], {k: snapshots.state_digest(row[k]) for k in ('cam_left', 'cam_right')})
        sensors = event['sensors']
        projected = np.array([float(sensors['collision']), 0. if sensors['collision_angle'] is None
            else float(sensors['collision_angle']), *sensors['wind_direction']], np.float32)
        _require(np.array_equal(row['sensors'], projected), 'Recorded policy sensor array differs')
        _same(event['observation_sha256'], snapshots.state_digest({
            'cam_left': row['cam_left'], 'cam_right': row['cam_right'], 'sensors': sensors}))
        cues = [e for e in events if e['kind'] == 'memory_cue' and e['tick'] == row['tick']]
        _require(len(cues) == 1 and cues[0]['bearing'] == sensors['wind_direction'], 'Policy has wrong actual bearing')


def _reference(event):
    return {'sequence': event['sequence'], 'sha256': memory.sha256(event)}


def _enveloped(event, kind, body_key, body, tick, owner):
    _fields(event, _ENVELOPE | {body_key})
    _same(event, {'sequence': event['sequence'], 'kind': kind, 'run_id': owner, 'episode': 0,
        'tick': tick, 'episode_step': tick, body_key: body})


def _replay(raw, context, application, case, source, source_world, projection, final_world, deadline):
    events, owner = raw['events'], context['run_id']
    b, n = context['schedule']['boundary_tick'], len(projection)
    restored_index, restored = oracle._single(events, 'application_restored', 'condition')
    configured_index, configured = oracle._single(events, 'memory_selector_configured', 'condition')
    armed_index, armed = oracle._single(events, 'memory_decision_armed', 'condition')
    for event in (restored, configured, armed): oracle._event_boundary(event, b, event['kind'])
    _same(restored.get('parent_run_id'), context['source_run_id'])
    _same(restored.get('parent_event_prefix'), application['event_prefix'])
    _same(restored.get('revision'), application['revision']); _same(restored.get('eyes'), {'left': True, 'right': True})
    initial_pose = projection[0]['pose'] if projection else raw['_source_last_pose']
    _same(restored.get('world', {}).get('pose'), initial_pose)
    _same(initial_pose, raw['_source_last_pose'])
    _same(restored['world'], {'arena': 7., 'pose': initial_pose, 'goal': [*case['goal_xy'], .25],
        'obstacles': [[*xy, .4] for xy in world.PROFILE['obstacles']]})
    retained = {k: v for k, v in source.items() if k not in ('u', 'selector')}
    _same(configured.get('retained_memory_sha256'), memory.sha256(retained))
    state = transition.configure_terminal_condition_vnext(source, configured.get('selector'), configured.get('u'), context=context)
    armed_world = world.arm(source_world, b, context['source_invariant_sha256'])
    _same(context['schedule'], {k: armed_world[k if k != 'boundary_tick' else 'armed_boundary_tick'] for k in context['schedule']})
    _same(armed.get('schedule'), {**context['schedule'], 'acquired_state_sha256': context['source_invariant_sha256']})
    state = transition.arm_terminal_state_vnext(state, boundary_tick=b, context=context)
    sensed = [e for e in events if e['kind'] == 'memory_sensed']
    tail = raw['manifest']['final_phase'] == 'failed'
    _require(len(sensed) == n + int(tail), 'Sensed packets differ from actual motor/tail cuts')
    _require([e['tick'] for e in sensed] == list(range(b, b + len(sensed))), 'Nonconsecutive sensed packets')
    _require(restored_index < configured_index < armed_index < sensed[0]['sequence'], 'Restore/configure/arm/sensing order differs')
    expected_world = copy.deepcopy(armed_world)
    expected_world['last_tick'] = b + n if tail else b + n - 1
    if context['schedule']['event_tick'] is not None and expected_world['last_tick'] >= context['schedule']['event_tick']:
        expected_world.update(applied=True, cue_state=1,
            gate_result='closed' if case['kind'] == 'change' else 'not_requested')
        oracle._gate_evidence(case, events, {**context['schedule'], 'acquired_state_sha256': context['source_invariant_sha256']}, expected_world)
    else:
        _require(not any(e['kind'] in ('memory_world_changed', 'intervention') for e in events), 'Unreached world change supplied')
    _same(final_world, world.validate_state(expected_world))
    binding = transition.OracleBinding(source['m'], case, source_world) if context['condition'] == 'oracle' else None
    chain, witnesses, commits = (0, memory.sha256(context)), [], []
    trigger_reached, decision_reached, terminal_result = False, False, None
    relevant = {'memory_transition_witness_vnext', 'memory_transition_commit_vnext', 'memory_decision',
        'memory_inspected', 'memory_cue', 'neural_policy_call', 'runtime_failure', 'episode_finished'}
    consumed = set()
    for offset, sensed_event in enumerate(sensed):
        _deadline(deadline)
        tick = b + offset
        _fields(sensed_event, _ENVELOPE | {'packet'})
        pose = projection[offset]['pose'] if offset < n else (projection[-1]['next_pose'] if n else raw['_source_last_pose'])
        inputs = world.reconstruct_inputs(case, pose, tick,
            event_tick=context['schedule']['event_tick'], gate_result=expected_world['gate_result'])
        packet = decision.capture_symbolic(*inputs, episode_id=state['episode_id'], tick=tick)
        _same(sensed_event['packet'], packet)
        refs = {'cue_event': None, 'gate_event': None, 'intervention_event': None}
        for event in events[:sensed_event['sequence']]:
            if event['kind'] == 'memory_world_changed':
                role = 'cue_event' if event.get('detail', {}).get('kind') == 'memory_cue_changed' else 'gate_event'
                refs[role] = _reference(event)
            elif event['kind'] == 'intervention': refs['intervention_event'] = _reference(event)
        # Every actual edit must already precede sensing at its scheduled tick.
        if context['schedule']['event_tick'] is not None and tick >= context['schedule']['event_tick']:
            _require(refs['cue_event'] is not None, 'World event follows its sensed packet')
            if case['kind'] == 'change': _require(refs['gate_event'] is not None and refs['intervention_event'] is not None, 'Gate edit is not reached')
        reach = {**refs, 'sensed_event': _reference(sensed_event), 'before_occupancy': None,
            'after_occupancy': None, 'actual_circles': inputs[2]}
        result = transition.advance_transition_vnext(state, packet, context=context, oracle_binding=binding,
            reach=reach, job_sha256=raw['job']['sha256'], chain=chain)
        _require(result.status not in ('rejected', 'idempotent'), 'Unscored infrastructure or duplicate transition')
        end = sensed[offset + 1]['sequence'] if offset + 1 < len(sensed) else len(events)
        window = [e for e in events[sensed_event['sequence'] + 1:end] if e['kind'] in relevant]
        cursor = 0
        def take(kind):
            nonlocal cursor
            _require(cursor < len(window) and window[cursor]['kind'] == kind, 'Missing or reordered actual transition event: ' + kind)
            event = window[cursor]; cursor += 1; consumed.add(event['sequence'])
            _require(event['tick'] == tick or kind == 'episode_finished' and event['tick'] == tick + 1, 'Wrong transition event tick')
            return event
        if result.witness is not None:
            event = take('memory_transition_witness_vnext')
            _enveloped(event, event['kind'], 'witness', result.witness, tick, owner)
            transition.terminal_event_bytes_vnext(event['kind'], event['witness'], sequence=event['sequence'],
                run_id=owner, episode=0, tick=tick, episode_step=tick)
            witnesses.append(_reference(event))
            chain = (chain[0] + 1, memory.sha256(result.witness))
            trigger_reached |= result.witness['trigger'] is not None
        if result.status == 'raised':
            _require(offset == n and result.witness['exception']['type'] == 'CueUnavailable', 'Unscored unknown or row-backed exception')
            terminal_result = result
            failure = take('runtime_failure')
            expected_error = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick,
                **result.witness['exception'], 'policy_diagnostics': {}}
            _enveloped(failure, 'runtime_failure', 'error', expected_error, tick, owner)
        else:
            state = result.proposed_state
            if result.witness is not None:
                event = take('memory_transition_commit_vnext')
                body = {'schema': transition.COMMIT_SCHEMA, 'context_sha256': memory.sha256(context),
                    'witness_sha256': memory.sha256(result.witness), 'tick': tick,
                    'memory_sha256': memory.sha256(state), 'lifecycle': state['terminal_lifecycle']}
                _enveloped(event, event['kind'], 'commit', body, tick, owner)
                transition.terminal_event_bytes_vnext(event['kind'], body, sequence=event['sequence'],
                    run_id=owner, episode=0, tick=tick, episode_step=tick)
                commits.append(_reference(event))
            for detail in result.decisions:
                event = take('memory_decision')
                _fields(event, _ENVELOPE | {'detail', 'route_anchor'})
                _same(event['detail'], detail); _same(event['route_anchor'], {'stage': 'pre-control', 'xy': pose[:2]})
                trigger_reached |= detail.get('kind') == 'memory_trigger'
            event = take('memory_inspected')
            _enveloped(event, 'memory_inspected', 'memory', transition.inspect_terminal_state_vnext(state, context=context), tick, owner)
            if state['supervisor']['phase'] == 'failure':
                _require(offset == n and tail, 'Returned supervisor failure has a motor row')
                terminal_result = result
                failure = take('runtime_failure')
                expected_error = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick, 'type': 'ValueError',
                    'message': 'Memory-v2 supervisor failure: ' + state['supervisor']['failure_reason'], 'policy_diagnostics': {}}
                _enveloped(failure, 'runtime_failure', 'error', expected_error, tick, owner)
            else:
                _require(offset < n, 'Unproved sensor-only terminal')
                cue = take('memory_cue'); _fields(cue, _ENVELOPE | {'bearing', 'raw_upstream_bearing'})
                _same(cue['bearing'], result.bearing)
                _require(type(cue['raw_upstream_bearing']) is list and len(cue['raw_upstream_bearing']) == 2
                    and all(type(x) is float and math.isfinite(x) for x in cue['raw_upstream_bearing']), 'Invalid upstream bearing')
                take('neural_policy_call')
                if not tail and offset == n - 1:
                    take('episode_finished')
        # CueUnavailable is raised only at the ordinary final bridge cut, after
        # any due local decision. Local reach does not imply Engine assignment.
        decision_reached |= tick >= context['schedule']['decision_tick']
        _require(cursor == len(window), 'Unexpected progress or transaction after terminal cut')
    _require(all(e['sequence'] in consumed for e in events if e['kind'] in relevant), 'Transition event outside actual packet windows')
    _require(len(witnesses) <= 2 and len(commits) <= 2, 'Transaction count exceeds fixed bound')
    if tail:
        _require(terminal_result is not None, 'Missing independently replayed natural terminal cause')
        failure = next(e for e in events if e['kind'] == 'runtime_failure')
        _same(raw['manifest']['last_outcome'], failure['error'])
        _require(not any(e['kind'] != 'chunk' for e in events[failure['sequence'] + 1:]), 'Postterminal progress')
    else:
        _require(n > 0 and decision_reached, 'Normal outcome lacks full reached decision proof')
        legacy._normal_condition_terminal(events, raw['manifest'], {'manifest_status': 'completed',
            'final_phase': raw['manifest']['final_phase'], 'total_ticks': b + n, 'last_tick': b + n - 1}, context['schedule'])
        _, terminal_event = oracle._single(events, 'episode_finished', 'normal terminal')
        _same(terminal_event['outcome'], raw['manifest']['last_outcome'])
        _same(terminal_event['metrics'], raw['manifest']['metrics'])
        outcome = raw['manifest']['last_outcome']
        if outcome['reason'] == 'goal':
            _require(transition.terminal_goal_allowed_vnext(state, context=context), 'Goal without inspected permitted route')
            distance = float(np.linalg.norm(np.asarray(projection[-1]['next_pose'][:2]) - np.asarray(case['goal_xy'])))
            _require(distance < .25 and distance == outcome['final_distance'], 'Goal differs from reached physical row geometry')
    return witnesses, commits, trigger_reached, decision_reached


def prove_terminal_vnext(raw, *, context, source_application, source_events, source_rows, deadline):
    """Replay supplied evidence; returned proof remains conditional on its inputs.

    No actual job body or SNP/native/container byte authority is available through
    this API. Public audit/validate and held-source admission deliberately do not
    exist in Task3a, rather than returning fabricated receipts or success flags.
    """
    _deadline(deadline)
    _fields(raw, _RAW_KEYS); _fields(raw['descriptors'], _DESCRIPTORS)
    c = transition.validate_context_vnext(context)
    # Engine stops after its 900th motor row. A later sensed packet is already
    # postterminal, even if the pure worker could return continuation_timeout.
    # Check this bounded semantic fact before materializing any writer bytes.
    m = raw['manifest']
    _require(type(m) is dict and type(raw['rows']) is list, 'Invalid condition manifest/rows')
    n = _int(m.get('recorded_ticks'), 900)
    _require(n == len(raw['rows']), 'Recorded motor-row count differs')
    total = _int(m.get('total_tick'))
    b = c['schedule']['boundary_tick']
    _require(total == b + n, 'Terminal cut differs from acquired motor interval')
    _require(m.get('final_phase') in ('failed', 'terminated', 'truncated'), 'No incomplete terminal phase')
    _same(m.get('status'), 'failed' if m['final_phase'] == 'failed' else 'completed')
    if m['final_phase'] == 'failed':
        _require(n < 900 and total < min(2100, b + 900), 'Forbidden postterminal sensor tail')
    descriptors = raw['descriptors']
    transition.validate_descriptor_vnext(raw['job'], max_bytes=_MIB)
    _same(raw['job'], descriptors['job'])
    _descriptor(descriptors['context'], memory.canonical_bytes(c), transition.CONTEXT_MAX_BYTES)
    _events(raw['events'], c['run_id'])
    manifest_bytes, event_bytes, report_bytes = (_writer(raw['manifest']),
        b''.join(_writer(e) for e in raw['events']), memory.canonical_bytes(raw['worker_report']))
    for role, payload, maximum in (('raw_manifest', manifest_bytes, _MIB),
            ('raw_events', event_bytes, 5 * _MIB), ('worker_report', report_bytes, _MIB)):
        _descriptor(descriptors[role], payload, maximum)
    _require(len(manifest_bytes) + len(report_bytes) + len(memory.canonical_bytes(c)) <= _MIB,
        'Known metadata exceeds unchanged shared overhead ceiling')
    case, source, source_world, source_projection = _source(source_application, source_events, source_rows, c)
    _deadline(deadline)
    b, n, final_world = _manifest(raw, c, source_application, case)
    chunks = _chunks(raw['events'], b, n)
    _decoded_rows(raw['rows'], 900, 384 * _MIB)
    if n:
        projection, cameras, row_sequence = legacy._audit_rows(raw['rows'], 'condition')
        _require(projection[0]['tick'] == b, 'Condition rows do not start at acquired boundary')
        compact_rows = compact._project_rows(raw['rows'], 'condition')
        trace = compact._trace_digest(compact_rows)
    else:
        projection = []
        cameras = row_sequence = trace = hashlib.sha256().hexdigest()
    _policy(raw['rows'], raw['events'])
    expected_metrics = copy.deepcopy(source_application['metrics'])
    continuation_path = 0.
    for row in raw['rows']:
        distance = float(np.linalg.norm(row['next_pose'][:2] - row['pose'][:2]))
        continuation_path += distance
        expected_metrics['reward'] += float(row['reward'])
        expected_metrics['contact_ticks'] += int(bool(row['sensors'][0]))
        expected_metrics['path_length'] += distance
    _same(raw['manifest']['metrics'], expected_metrics)
    # Internal detached datum avoids inventing an application pose field.
    replay_raw = {**raw, '_source_last_pose': source_projection[-1]['next_pose']}
    witnesses, commits, trigger_reached, decision_reached = _replay(replay_raw, c, source_application,
        case, source, source_world, projection, final_world, deadline)
    goal = raw['manifest']['last_outcome'].get('reason') == 'goal'
    result = {'schema': 'memory-terminal-proof-vnext-v1', **copy.deepcopy(descriptors),
        'source_snapshot': copy.deepcopy(c['source_snapshot']), 'boundary_tick': b,
        'terminal_sensor_tick': b + n if raw['manifest']['final_phase'] == 'failed' else None,
        'first_motor_tick': b if n else None, 'last_motor_tick': b + n - 1 if n else None,
        'row_count': n, 'chunk_count': len(chunks), 'world_applied': final_world['applied'],
        'trigger_reached': trigger_reached, 'decision_reached': decision_reached,
        'witnesses': witnesses, 'commits': commits, 'outcome': copy.deepcopy(raw['manifest']['last_outcome']),
        'goal': goal, 'path_length': continuation_path, 'capped_ticks': n if goal else 900,
        'trace_digest': trace, 'row_sequence_sha256': row_sequence,
        'camera_sequence_sha256': cameras, 'invariant': c['source_invariant_sha256']}
    _fields(result, PROOF_KEYS)
    _deadline(deadline)
    return copy.deepcopy(result)
