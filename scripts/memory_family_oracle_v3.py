"""Admit evaluator-only oracle evidence from retained memory-family records.

The caller owns checksum-validating and decoding the supplied records.  This
module is pure: it opens no files, fits no artifact, and invokes no selector.
"""
import copy
import math
import uuid

from palimpsest import artifacts, memory, memory_decision, memory_decision_world as world
from palimpsest import memory_task, memory_world
from palimpsest.memory_experiment import CONDITIONS, gold_target_ids, selection_for_condition


MAX_EVENTS = 50_000
MAX_ROWS = 2_100
MAX_INPUT_BYTES = 32 * 1024 * 1024
APPLICATION_FIELDS = {'schema_version', 'source_run_id', 'event_prefix',
    'teacher_reset_identity', 'controller', 'episode', 'total_tick', 'revision',
    'eyes', 'scenario', 'texture', 'episode_step', 'phase', 'manual_action',
    'metrics', 'last_outcome', 'seed', 'episode_finished', 'pending_commands',
    'session_exhausted', 'recording_failed', 'receipts', 'original_commands',
    'memory', 'world_task_state', 'controller_tensors', 'execution_mode', 'task_state'}
RUN_BOUND_EVENTS = {'episode_started', 'application_restored', 'memory_sensed',
    'memory_decision', 'memory_acquired_boundary', 'memory_selector_configured',
    'memory_decision_armed', 'memory_world_changed', 'intervention', 'runtime_failure'}


def _plain(value):
    """Normalize decoded numeric arrays without accepting opaque objects."""
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _plain(child) for key, child in value.items()}
    if type(value) in (list, tuple):
        return [_plain(child) for child in value]
    if hasattr(value, 'tolist'):
        return _plain(value.tolist())
    if hasattr(value, 'item'):
        return _plain(value.item())
    raise ValueError('Oracle evidence requires decoded JSON values')


def _bounded(value, label):
    value = _plain(value)
    if len(memory.canonical_bytes(value)) > MAX_INPUT_BYTES:
        raise ValueError(f'{label} exceeds oracle evidence bound')
    return value


def _required(value, fields, label):
    if type(value) is not dict or not set(fields).issubset(value):
        raise ValueError(f'{label} lacks required fields')


def _run_id(value):
    try:
        valid = type(value) is str and uuid.UUID(value).hex == value
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Run ID must be canonical UUID hex')


def _event_boundary(event, tick, label):
    if any(type(event.get(key)) is not int for key in ('episode', 'episode_step', 'tick')):
        raise ValueError(f'{label} lacks an exact recorded boundary')
    if (event['episode'], event['episode_step'], event['tick']) != (0, tick, tick):
        raise ValueError(f'{label} differs from its recorded boundary')


def _single(events, kind, label):
    found = [(index, event) for index, event in enumerate(events) if event.get('kind') == kind]
    if len(found) != 1:
        raise ValueError(f'{label} requires exactly one {kind} event')
    return found[0]


def _events(value, run_id, label):
    value = _bounded(value, label)
    if type(value) is not list or len(value) > MAX_EVENTS or any(type(event) is not dict for event in value):
        raise ValueError(f'Invalid bounded {label}')
    last_boundary = -1
    for index, event in enumerate(value):
        if type(event.get('kind')) is not str:
            raise ValueError(f'{label} contains an untyped event')
        if type(event.get('sequence')) is not int or event['sequence'] != index:
            raise ValueError(f'{label} event sequence differs')
        if event['kind'] in RUN_BOUND_EVENTS:
            if event.get('run_id') != run_id:
                raise ValueError(f'{label} event belongs to another run')
            if (any(type(event.get(key)) is not int
                    for key in ('episode', 'episode_step', 'tick'))
                    or event['episode'] != 0 or event['tick'] != event['episode_step']
                    or event['episode_step'] < last_boundary):
                raise ValueError(f'{label} run-bound events violate native tick order')
            last_boundary = event['episode_step']
    return value


def _rows(value, start, label):
    value = _bounded(value, label)
    if type(value) is not list or not value or len(value) > MAX_ROWS:
        raise ValueError(f'Invalid bounded {label}')
    for row in value:
        if type(row) is not dict or set(row) != {'episode', 'tick', 'pose', 'next_pose'}:
            raise ValueError(f'{label} must be the exact audit row projection')
        if type(row['episode']) is not int or row['episode'] != 0 or type(row['tick']) is not int:
            raise ValueError(f'{label} has an invalid episode/tick')
        row['pose'] = memory_world._numbers(row['pose'], 3)
        row['next_pose'] = memory_world._numbers(row['next_pose'], 3)
    if [row['tick'] for row in value] != list(range(start, start + len(value))):
        raise ValueError(f'{label} ticks are not consecutive from the declared boundary')
    if any(before['next_pose'] != after['pose'] for before, after in zip(value, value[1:])):
        raise ValueError(f'{label} poses do not form one recorded control trace')
    return value


def _validate_bindings(value, source_run_id):
    value = _bounded(value, 'oracle bindings')
    memory._fields(value, 'protocol_sha256 plan_sha256 source_identity_sha256 source post')
    for key in ('protocol_sha256', 'plan_sha256', 'source_identity_sha256'):
        memory._digest(value[key])
    memory._fields(value['source'], 'run_id recording_sha256 report_sha256 snapshot_sha256')
    memory._fields(value['post'], 'run_id condition recording_sha256 report_sha256 source_snapshot_sha256 selector_sha256 u_sha256 history_sha256 history_bundle_sha256')
    for part in ('source', 'post'):
        _run_id(value[part]['run_id'])
        for key, child in value[part].items():
            if key.endswith('_sha256'):
                memory._digest(child)
    if (value['source']['run_id'] != source_run_id
            or value['post']['run_id'] == source_run_id
            or value['post']['condition'] != 'own'
            or value['post']['source_snapshot_sha256'] != value['source']['snapshot_sha256']):
        raise ValueError('Oracle source/post bindings differ')
    return value


def _application(case, value):
    value = _bounded(value, 'source application')
    if type(value) is not dict or set(value) != APPLICATION_FIELDS:
        raise ValueError('Source application differs from the Engine snapshot contract')
    if (type(value['schema_version']) is not int or value['schema_version'] != 8
            or value['scenario'] != world.SCENARIO or value['controller'] != 'flynn'
            or type(value['episode']) is not int or value['episode'] != 0
            or type(value['total_tick']) is not int or type(value['episode_step']) is not int
            or value['total_tick'] != value['episode_step'] or value['episode_step'] <= 0
            or value['phase'] != 'paused' or value['seed'] != case['seed']
            or value['texture'] != 'checker' or value['execution_mode'] not in ('live', 'policy')):
        raise ValueError('Source is not the paused acquired CPU FLYNN boundary')
    for key in ('total_tick', 'episode_step', 'revision'):
        memory._int(value[key])
    if (value['episode_step'] > 2100 or value['teacher_reset_identity'] is not None
            or value['eyes'] != {'left': True, 'right': True}
            or value['manual_action'] != [0., 0.] or value['task_state'] is not None
            or value['last_outcome'] is not None or value['episode_finished'] is not False
            or value['session_exhausted'] is not False or value['recording_failed'] is not False):
        raise ValueError('Source application is terminal or outside the decision profile')
    memory._fields(value['controller_tensors'], 'graph_buffers parameters')
    for digest in value['controller_tensors'].values():
        memory._digest(digest)
    memory._fields(value['metrics'], 'reward contact_ticks path_length')
    if (any(type(item) not in (int, float) or isinstance(item, bool) or not math.isfinite(item)
            for item in value['metrics'].values())
            or type(value['metrics']['contact_ticks']) is not int
            or value['metrics']['contact_ticks'] < 0 or value['metrics']['path_length'] < 0):
        raise ValueError('Source application metrics are invalid')
    originals, receipts, pending = (value['original_commands'], value['receipts'],
                                     value['pending_commands'])
    from palimpsest.engine import Engine
    if (type(originals) is not dict or type(receipts) is not dict
            or set(originals) != set(receipts) or len(originals) > Engine.MAX_IDS
            or type(pending) is not list or len(pending) > Engine.MAX_QUEUE):
        raise ValueError('Source application command queues are invalid')
    probe = Engine.__new__(Engine)
    probe.body_state, probe.scenario = None, world.SCENARIO
    for identifier, original in originals.items():
        receipt = receipts[identifier]
        if (probe._validate_command(original) != original or original['id'] != identifier
                or type(receipt) is not dict or receipt.get('id') != identifier
                or receipt.get('status') not in ('queued', 'applied', 'rejected', 'failed')):
            raise ValueError('Source application receipt history is invalid')
    normalized = [probe._validate_command(command) for command in pending]
    if (pending or any(receipt['status'] == 'queued' for receipt in receipts.values())
            or len({command['id'] for command in normalized}) != len(normalized)
            or any(originals.get(command['id']) != command for command in normalized)
            or {command['id'] for command in normalized}
               != {identifier for identifier, receipt in receipts.items()
                   if receipt['status'] == 'queued'}):
        raise ValueError('Source application pending queue is invalid')
    _run_id(value['source_run_id'])
    memory._fields(value['event_prefix'], 'sha256 size_bytes event_count')
    memory._digest(value['event_prefix']['sha256'])
    memory._int(value['event_prefix']['size_bytes'])
    memory._int(value['event_prefix']['event_count'])
    task = memory_decision.validate_state(value['memory'])
    source_world = world.validate_state(value['world_task_state'])
    boundary = value['episode_step']
    if (task['graph'] != world.public_graph(case)
            or task['initial_m'] != {'version': 1, 'facts': case['facts']}
            or not memory_decision.acquired_boundary(task)
            or task['cursor']['tick'] != boundary - 1
            or task['supervisor']['decision_tick'] is not None
            or task['supervisor']['continuation_start_tick'] is not None
            or source_world['case'] != case or source_world['last_tick'] != boundary - 1
            or source_world['armed_boundary_tick'] is not None
            or source_world['event_tick'] is not None or source_world['decision_tick'] is not None
            or source_world['acquired_state_sha256'] is not None or source_world['applied']):
        raise ValueError('Source memory/world cursors differ from the acquired boundary')
    expected_selector = {'version': 1, 'condition': 'no-U', 'limit': 1, 'resource': None,
        'resource_sha256': memory.sha256(None), 'provenance_sha256': case['profile_sha256']}
    if (task['e'] != {'version': 1, 'episodes': []}
            or task['u'] != memory.artifact(method='empty-v1')
            or task['selector'] != expected_selector):
        raise ValueError('Source acquisition contains nonempty history/U or a privileged selector')
    return value, task, source_world, boundary


def _recorded_packets(case, events, rows, episode_id, *, event_tick=None, gate_result='pending', through=None):
    sensed = {}
    for event in events:
        if event.get('kind') != 'memory_sensed':
            continue
        tick = event.get('episode_step')
        _event_boundary(event, tick, 'memory_sensed')
        if tick in sensed:
            raise ValueError('Duplicate recorded symbolic packet tick')
        sensed[tick] = event.get('packet')
    end = rows[-1]['tick'] if through is None else through
    needed = range(rows[0]['tick'], end + 1)
    row_by_tick = {row['tick']: row for row in rows}
    if any(tick not in row_by_tick or tick not in sensed for tick in needed):
        raise ValueError('Oracle evidence omits a required packet or actual-pose row')
    packets = []
    for tick in needed:
        row = row_by_tick[tick]
        private, pose, circles = world.reconstruct_inputs(case, row['pose'], tick,
            event_tick=event_tick, gate_result=gate_result)
        expected = memory_decision.capture_symbolic(private, pose, circles,
            episode_id=episode_id, tick=tick)
        if memory.canonical_bytes(sensed[tick]) != memory.canonical_bytes(expected):
            raise ValueError('Recorded packet differs from actual-pose frozen geometry reconstruction')
        packets.append(expected)
    return packets, sensed


def _occupancy(case, circles):
    labels = memory_world.passage_status(circles)
    return {subject: labels[side]
            for subject, side in zip(case['subjects_by_side'], memory_world.SUBJECTS)}


def _expected_geometry(case):
    before = [[*xy, .4] for xy in world.PROFILE['obstacles']]
    after = copy.deepcopy(before)
    if case['kind'] == 'change':
        side = case['subjects_by_side'].index(case['closure_subject_id'])
        after[len(world.POSTS) + side][:2] = world.CLOSED_GATES[side].copy()
    return before, after


def _source_evidence(case, application, events, rows):
    task, source_world, boundary = application['memory'], application['world_task_state'], application['episode_step']
    if len(rows) != boundary:
        raise ValueError('Source rows do not cover the exact acquired prefix')
    forbidden = {'application_restored', 'intervention', 'memory_world_changed',
        'memory_selector_configured', 'memory_decision_armed'}
    if any(event['kind'] in forbidden for event in events):
        raise ValueError('Fresh source acquisition contains continuation/world edits')
    started_index, started = _single(events, 'episode_started', 'source acquisition')
    _event_boundary(started, 0, 'source episode_started')
    started_world = artifacts._world_at(events, 0, 0)
    if started.get('seed') != case['seed'] or rows[0]['pose'] != started_world['pose']:
        raise ValueError('Source episode seed differs from the case')
    acquired_index, acquired = _single(events, 'memory_acquired_boundary', 'source acquisition')
    _event_boundary(acquired, boundary, 'memory_acquired_boundary')
    if (acquired.get('boundary_tick') != boundary
            or acquired.get('acquired_evidence') != task['supervisor']['acquired_evidence']):
        raise ValueError('Recorded acquired boundary differs from retained memory')
    packet_indices = [index for index, event in enumerate(events)
                      if event.get('kind') == 'memory_sensed']
    if not packet_indices or not started_index < min(packet_indices) <= max(packet_indices) < acquired_index:
        raise ValueError('Source start, packets and acquired boundary are not ordered')
    packets, sensed = _recorded_packets(case, events, rows, task['episode_id'],
        gate_result=source_world['gate_result'])
    if set(sensed) != set(range(boundary)):
        raise ValueError('Source symbolic packet range differs from its exact rows')
    observations = [sample for packet in packets for sample in packet['passages']
                    if sample['passability'] != 'unobserved']
    by_id = {sample['id']: sample for sample in observations}
    if len(by_id) != len(observations):
        raise ValueError('Source reused an observation ID')
    for fact in task['m']['facts']:
        evidence = fact['evidence']
        sample = None if evidence is None else by_id.get(evidence['id'])
        if (fact['status'] != 'observed' or fact['estimate'] != 'open' or sample is None
                or {key: sample[key] for key in ('id', 'episode_id', 'tick')} != evidence
                or sample['subject_id'] != fact['subject_id'] or sample['passability'] != 'open'):
            raise ValueError('Acquired fact lacks its exact reconstructed open observation')
    acquired_samples = task['supervisor']['acquired_evidence']
    if any(by_id.get(sample['id']) != sample for sample in acquired_samples.values()):
        raise ValueError('Acquired evidence bank differs from reconstructed source packets')
    final_packet = packets[-1]
    expected_detector = {'tick': boundary - 1, 'cues': [
        {'id': cue['id'], 'state': cue['state'],
         'observation_id': memory_task._sensor_id(task['episode_id'], boundary - 1, 'cue', cue['id'])}
        for cue in sorted(final_packet['cues'], key=lambda item: item['id'])]}
    if (task['detector'] != expected_detector
            or task['cursor']['packet_sha256'] != memory.sha256(final_packet)):
        raise ValueError('Source detector/cursor differs from its final reconstructed packet')
    replayed = _replay_packets(
        memory_decision.initialize(case), packets, events, end_index=acquired_index)
    if memory.canonical_bytes(replayed) != memory.canonical_bytes(task):
        raise ValueError('Acquired source memory differs from pure packet replay')
    return packets, observations


def _selector(events, boundary, task, case, bindings):
    index, event = _single(events, 'memory_selector_configured', 'post continuation')
    _event_boundary(event, boundary, 'memory_selector_configured')
    _required(event, ('selector', 'u', 'retained_memory_sha256'), 'memory_selector_configured')
    u = memory.validate_u(event['u'])
    selector = memory_task.validate_selector(event['selector'], task['m'], u)
    retained = {key: value for key, value in task.items() if key not in ('u', 'selector')}
    provenance = u['provenance']
    if (selector['condition'] != 'own' or selector['resource'] is not None
            or u['payload']['rules'] != [{'trigger': 'cue_changed', 'relation': case['regime']}]
            or provenance['method'] != 'history-fit-v1'
            or provenance['history_sha256'] != bindings['post']['history_sha256']
            or provenance['protocol_sha256'] != memory.PROTOCOL_SHA256
            or provenance['producer_sha256'] != memory.PRODUCER_SHA256
            or selector['provenance_sha256'] != bindings['post']['history_bundle_sha256']
            or memory.sha256(selector) != bindings['post']['selector_sha256']
            or memory.sha256(u) != bindings['post']['u_sha256']
            or event['retained_memory_sha256'] != memory.sha256(retained)):
        raise ValueError('Oracle donor must be an isolated non-oracle own continuation')
    return index, selector, u


def _schedule(case, events, boundary, post_world, acquired_state_sha256):
    index, event = _single(events, 'memory_decision_armed', 'post continuation')
    _event_boundary(event, boundary, 'memory_decision_armed')
    profile = world.registered_profile(case['profile_sha256'])
    expected = {'boundary_tick': boundary,
        'event_tick': None if not case['event_enabled'] else boundary + profile['arm_schedule']['event_offset'],
        'decision_tick': boundary + profile['arm_schedule']['decision_offset'],
        'acquired_state_sha256': acquired_state_sha256}
    retained = {'boundary_tick': post_world['armed_boundary_tick'],
        'event_tick': post_world['event_tick'], 'decision_tick': post_world['decision_tick'],
        'acquired_state_sha256': post_world['acquired_state_sha256']}
    if event.get('schedule') != expected or retained != expected:
        raise ValueError('Registered family schedule differs from retained continuation')
    return index, expected


def _gate_evidence(case, events, schedule, post_world):
    changes = [(index, event) for index, event in enumerate(events)
               if event.get('kind') == 'memory_world_changed']
    interventions = [(index, event) for index, event in enumerate(events)
                     if event.get('kind') == 'intervention']
    if case['kind'] == 'no-event':
        if changes or interventions or post_world['applied'] or post_world['cue_state'] != 0:
            raise ValueError('No-event case contains a world event')
        return None, None, None
    event_tick = schedule['event_tick']
    cue = {'kind': 'memory_cue_changed', 'tick': event_tick, 'cue_id': case['cue_id'],
           'before': 0, 'after': 1}
    cue_events = [(index, event) for index, event in changes if event.get('detail') == cue]
    if len(cue_events) != 1 or not post_world['applied'] or post_world['cue_state'] != 1:
        raise ValueError('Retained cue transition differs from the scheduled event')
    _event_boundary(cue_events[0][1], event_tick, 'memory_cue_changed')
    if case['kind'] == 'null':
        if len(changes) != 1 or interventions or post_world['gate_result'] != 'not_requested':
            raise ValueError('Null case contains a gate edit')
        return cue_events[0], None, None
    gates = [(index, event) for index, event in changes
             if event.get('detail', {}).get('kind') == 'memory_gate_applied']
    rejected = [event for _, event in changes
                if event.get('detail', {}).get('kind') == 'memory_gate_rejected']
    if (len(changes) != 2 or len(gates) != 1 or rejected or len(interventions) != 1
            or post_world['gate_result'] != 'closed'):
        raise ValueError('Change case lacks one accepted scheduled gate edit')
    gate_index, gate_event = gates[0]
    _event_boundary(gate_event, event_tick, 'memory_gate_applied')
    side = case['subjects_by_side'].index(case['closure_subject_id'])
    detail = gate_event.get('detail', {})
    edit = detail.get('intervention', {})
    if (set(detail) != {'kind', 'tick', 'subject_id', 'intervention'}
            or detail['tick'] != event_tick or detail['subject_id'] != case['closure_subject_id']
            or set(edit) != {'kind', 'old', 'new', 'simulation_time', 'index'}
            or edit['kind'] != 'move_obstacle' or edit['index'] != len(world.POSTS) + side
            or edit['old'] != {'xy': world.PARKED_GATES[side]}
            or edit['new'] != {'xy': world.CLOSED_GATES[side]}
            or type(edit['simulation_time']) not in (int, float)
            or isinstance(edit['simulation_time'], bool) or not math.isfinite(edit['simulation_time'])):
        raise ValueError('Actual gate edit differs from the frozen cylinder placement')
    intervention_index, intervention = interventions[0]
    _event_boundary(intervention, event_tick, 'intervention')
    if (intervention.get('change') != edit or intervention.get('origin') != 'memory_world_schedule'
            or not cue_events[0][0] < gate_index < intervention_index):
        raise ValueError('Gate edit lacks its ordered retained intervention proof')
    return cue_events[0], gates[0], interventions[0]


def _trigger_evidence(case, events, packets, schedule, m, selector, u):
    details = [(index, event, event.get('detail', {})) for index, event in enumerate(events)
               if event.get('kind') == 'memory_decision']
    triggers = [(index, event, detail) for index, event, detail in details
                if detail.get('kind') == 'memory_trigger']
    selections = [(index, event, detail) for index, event, detail in details
                  if detail.get('kind') == 'memory_selection']
    if case['kind'] == 'no-event':
        if triggers or selections:
            raise ValueError('No-event case invoked the selector')
        return None
    event_tick = schedule['event_tick']
    by_tick = {packet['tick']: packet for packet in packets}
    before = by_tick[event_tick - 1]['cues']
    after = by_tick[event_tick]['cues']
    if (len(before) != 1 or len(after) != 1 or before[0]['id'] != case['cue_id']
            or after[0]['id'] != case['cue_id'] or before[0]['state'] != 0 or after[0]['state'] != 1):
        raise ValueError('Scheduled trigger lacks consecutive visible cue observations')
    episode_id = next(fact['evidence']['episode_id'] for fact in m['facts'])
    trigger = memory.validate_trigger({'id': memory_task._sensor_id(episode_id, event_tick, 'trigger', case['cue_id']),
        'episode_id': episode_id, 'tick': event_tick, 'kind': 'cue_changed', 'cue_id': case['cue_id'],
        'before': 0, 'after': 1,
        'before_observation_id': memory_task._sensor_id(episode_id, event_tick - 1, 'cue', case['cue_id']),
        'observation_id': memory_task._sensor_id(episode_id, event_tick, 'cue', case['cue_id'])})
    if len(triggers) != 1 or len(selections) != 1:
        raise ValueError('Cue event requires one recorded trigger and selector invocation')
    packets = [index for index, event in enumerate(events)
               if event.get('kind') == 'memory_sensed' and event.get('episode_step') == event_tick]
    if len(packets) != 1 or not packets[0] < triggers[0][0] < selections[0][0]:
        raise ValueError('Packet, trigger and selector invocation are not ordered')
    for _, event, detail in (triggers[0], selections[0]):
        _event_boundary(event, event_tick, detail['kind'])
    if triggers[0][2] != {'kind': 'memory_trigger', 'tick': event_tick, 'trigger': trigger}:
        raise ValueError('Recorded trigger differs from consecutive actual cue packets')
    selection_detail = selections[0][2]
    if (set(selection_detail) != {'kind', 'tick', 'selection'}
            or selection_detail['tick'] != event_tick):
        raise ValueError('Recorded selector invocation has an invalid boundary')
    recorded = memory.validate_selection(selection_detail['selection'], m, trigger)
    expected = selection_for_condition(
        'own', m, trigger, u=u, limit=selector['limit'])
    if (recorded != selection_detail['selection']
            or memory.canonical_bytes(recorded) != memory.canonical_bytes(expected)):
        raise ValueError('Recorded own selection differs from the fitted historical U replay')
    return trigger


def _replay_packets(state, packets, events, *, tail_tick=None, end_index=None):
    ticks = {packet['tick'] for packet in packets}
    recorded = {tick: [] for tick in ticks}
    sensed = [(index, event) for index, event in enumerate(events)
              if event.get('kind') == 'memory_sensed']
    sensed_ticks = [event.get('episode_step') for _, event in sensed]
    if sensed_ticks != sorted(sensed_ticks) or len(sensed_ticks) != len(set(sensed_ticks)):
        raise ValueError('Post sensed packets are not in strict tick order')
    windows = {event['episode_step']: (index, sensed[offset + 1][0]
        if offset + 1 < len(sensed) else len(events) if end_index is None else end_index)
        for offset, (index, event) in enumerate(sensed)}
    for index, event in enumerate(events):
        if event.get('kind') != 'memory_decision':
            continue
        tick = event.get('episode_step')
        if tick not in ticks:
            if tail_tick is None or tick != tail_tick:
                raise ValueError('Memory decision falls outside retained control/tail ticks')
            continue
        _event_boundary(event, tick, 'memory_decision')
        if not windows[tick][0] < index < windows[tick][1]:
            raise ValueError('Memory decision falls outside its native sensed-event window')
        recorded[tick].append(event.get('detail'))
    for packet in packets:
        try:
            state, _, audit = memory_decision.advance_memory(state, packet)
        except Exception as error:
            raise ValueError('Recorded control row terminates before its physics step') from error
        if state['supervisor']['phase'] == 'failure':
            raise ValueError('Recorded control row follows a terminal supervisor decision')
        if memory.canonical_bytes(recorded[packet['tick']]) != memory.canonical_bytes(audit):
            raise ValueError('Recorded memory decisions differ from pure donor replay')
    return state


def _replay_post(task, selector, u, boundary, packets, events, tail_tick):
    state = memory_decision.arm(
        memory_decision.configure_selector(task, selector, u), boundary)
    return _replay_packets(state, packets, events, tail_tick=tail_tick)


def _post_tail(case, events, rows, post_world, schedule, episode_id, state):
    last_row, last_tick = rows[-1]['tick'], post_world['last_tick']
    tail = last_tick == last_row + 1
    expected_sensed = {row['tick'] for row in rows} | ({last_tick} if tail else set())
    sensed_events = [event for event in events if event.get('kind') == 'memory_sensed']
    if (len(sensed_events) != len(expected_sensed)
            or {event.get('episode_step') for event in sensed_events} != expected_sensed):
        raise ValueError('Post sensed packets differ from control rows and terminal boundary')
    failures = [(index, event) for index, event in enumerate(events)
                if event.get('kind') == 'runtime_failure']
    if last_tick == last_row:
        if failures:
            raise ValueError('Successful row-backed continuation contains a runtime failure')
        return
    if not tail or last_tick <= schedule['decision_tick']:
        raise ValueError('Post world differs from its recorded control-row boundary')
    sensed = [(index, event) for index, event in enumerate(events)
              if event.get('kind') == 'memory_sensed'
              and event.get('episode_step') == last_tick]
    if len(sensed) != 1 or len(failures) != 1 or sensed[0][0] >= failures[0][0]:
        raise ValueError('Terminal sensor-only tick lacks its ordered runtime failure')
    if any(event.get('kind') != 'chunk' for event in events[failures[0][0] + 1:]):
        raise ValueError('Recorded progress follows the terminal runtime failure')
    _event_boundary(failures[0][1], last_tick, 'runtime_failure')
    error = failures[0][1].get('error')
    expected_fields = {'reason', 'episode', 'steps', 'type', 'message', 'policy_diagnostics'}
    if (type(error) is not dict or set(error) != expected_fields
            or error['reason'] != 'runtime_failure' or error['episode'] != 0
            or error['steps'] != last_tick or type(error['message']) is not str):
        raise ValueError('Terminal sensor-only tick has an invalid runtime outcome')
    tail_row = {'episode': 0, 'tick': last_tick,
                'pose': rows[-1]['next_pose'], 'next_pose': rows[-1]['next_pose']}
    tail_packets, _ = _recorded_packets(case, events, [tail_row], episode_id,
        event_tick=schedule['event_tick'], gate_result=post_world['gate_result'])
    decisions = [(index, event) for index, event in enumerate(events)
                 if event.get('kind') == 'memory_decision'
                 and event.get('episode_step') == last_tick]
    for _, event in decisions:
        _event_boundary(event, last_tick, 'terminal memory_decision')
    try:
        terminal, _, audit = memory_decision.advance_memory(state, tail_packets[0])
    except Exception as expected:
        expected_type, expected_message, audit = type(expected).__name__, str(expected), []
    else:
        supervisor = terminal['supervisor']
        if supervisor['phase'] != 'failure':
            raise ValueError('Terminal sensor-only packet does not terminate the donor')
        expected_type = 'ValueError'
        expected_message = 'Memory-v2 supervisor failure: ' + supervisor['failure_reason']
    if ([event.get('detail') for _, event in decisions] != audit
            or any(not sensed[0][0] < index < failures[0][0] for index, _ in decisions)
            or error['type'] != expected_type or error['message'] != expected_message):
        raise ValueError('Terminal failure differs from pure donor replay')


def oracle_evidence(case, source_application, source_events, source_rows,
                    post_events, post_rows, post_world_state, bindings):
    """Build a proof from one acquired source and its retained own continuation."""
    case = world.validate_case(_plain(case))
    if case['version'] != 3:
        raise ValueError('Oracle admission requires a canonical memory-family v3 case')
    application, task, source_world, boundary = _application(case, source_application)
    bindings = _validate_bindings(bindings, application['source_run_id'])
    source_events = _events(source_events, bindings['source']['run_id'], 'source events')
    post_events = _events(post_events, bindings['post']['run_id'], 'post events')
    source_rows = _rows(source_rows, 0, 'source rows')
    post_rows = _rows(post_rows, boundary, 'post rows')
    post_world = world.validate_state(_plain(post_world_state))
    if post_world['case'] != case or post_world['profile_sha256'] != case['profile_sha256']:
        raise ValueError('Post world belongs to another family case/profile')

    source_packets, source_observations = _source_evidence(
        case, application, source_events, source_rows)
    restored_index, restored = _single(post_events, 'application_restored', 'post continuation')
    _event_boundary(restored, boundary, 'application_restored')
    if (restored.get('parent_run_id') != bindings['source']['run_id']
            or restored.get('parent_event_prefix') != application['event_prefix']
            or restored.get('revision') != application['revision']
            or restored.get('eyes') != application['eyes']):
        raise ValueError('Post continuation did not restore the bound source run')
    selector_index, selector, u = _selector(post_events, boundary, task, case, bindings)
    acquired = copy.deepcopy(application)
    acquired.pop('source_run_id')
    acquired.pop('event_prefix')
    acquired['memory'].pop('u')
    acquired['memory'].pop('selector')
    acquired_state_sha256 = memory.sha256(acquired)
    arm_index, schedule = _schedule(
        case, post_events, boundary, post_world, acquired_state_sha256)
    if not restored_index < selector_index < arm_index:
        raise ValueError('Restore, selector and arm events are not ordered')
    first_sensed_index = next(index for index, event in enumerate(post_events)
                              if event.get('kind') == 'memory_sensed')
    if arm_index >= first_sensed_index:
        raise ValueError('Decision arm was not retained before continuation sensing')
    if post_world['last_tick'] < schedule['decision_tick']:
        raise ValueError('Post rows do not reach and bind the declared decision boundary')

    source_actual_world = artifacts._world_at(
        source_events, 0, boundary - 1, source_rows[-1]['next_pose'])
    restored_world = artifacts._world_at(post_events, 0, boundary)
    if (source_actual_world != restored_world
            or post_rows[0]['pose'] != restored_world['pose']):
        raise ValueError('Restored world differs from the actual acquired source boundary')
    before_geometry, after_geometry = _expected_geometry(case)
    if (source_actual_world['arena'] != world.PROFILE['arena']
            or source_actual_world['goal'][:2] != case['goal_xy']
            or source_actual_world['obstacles'] != before_geometry):
        raise ValueError('Source recording differs from the independently reconstructed geometry')

    cue_event, gate_event, intervention_event = _gate_evidence(case, post_events, schedule, post_world)
    after_world = artifacts._world_at(post_events, 0, schedule['decision_tick'])
    if (after_world['arena'] != source_actual_world['arena']
            or after_world['goal'] != source_actual_world['goal']
            or after_world['obstacles'] != after_geometry):
        raise ValueError('Post recording differs from the independently reconstructed geometry')

    all_post_packets, _ = _recorded_packets(case, post_events, post_rows, task['episode_id'],
        event_tick=schedule['event_tick'], gate_result=post_world['gate_result'])
    post_packets = [packet for packet in all_post_packets
                    if packet['tick'] <= schedule['decision_tick']]
    if any(sample['passability'] != 'unobserved'
            for packet in post_packets for sample in packet['passages']):
        raise ValueError('Fresh passage evidence arrived before route commitment')
    trigger = _trigger_evidence(
        case, post_events, post_packets, schedule, task['m'], selector, u)
    commitments = [(index, event, event.get('detail', {}))
                   for index, event in enumerate(post_events)
                   if event.get('kind') == 'memory_decision'
                   and event.get('detail', {}).get('kind') == 'memory_commitment'
                   and event.get('detail', {}).get('tick') == schedule['decision_tick']]
    if len(commitments) != 1:
        raise ValueError('Post continuation lacks one decision-boundary commitment')
    _event_boundary(commitments[0][1], schedule['decision_tick'], 'memory_commitment')
    decision_packet_index = next(index for index, event in enumerate(post_events)
        if event.get('kind') == 'memory_sensed'
        and event.get('episode_step') == schedule['decision_tick'])
    if commitments[0][0] <= decision_packet_index:
        raise ValueError('Decision commitment precedes its recorded packet')
    tail_tick = (post_world['last_tick'] if post_world['last_tick'] == post_rows[-1]['tick'] + 1
                 else None)
    replayed = _replay_post(
        task, selector, u, boundary, all_post_packets, post_events, tail_tick)
    _post_tail(case, post_events, post_rows, post_world, schedule,
               task['episode_id'], replayed)

    before_occupancy = _occupancy(case, before_geometry)
    after_occupancy = _occupancy(case, after_geometry)
    targets = gold_target_ids(task['m'], before_occupancy, after_occupancy, trigger)
    if ((case['kind'] == 'change' and len(targets) != 1)
            or (case['kind'] != 'change' and targets)):
        raise ValueError('Family event does not produce its declared change/null oracle target')
    event_packet_index = next((index for index, event in enumerate(post_events)
        if event.get('kind') == 'memory_sensed' and event.get('episode_step') == schedule['event_tick']), None)
    if case['event_enabled'] and (event_packet_index is None or cue_event[0] >= event_packet_index):
        raise ValueError('Cue/world transition was not retained before its symbolic packet')
    if gate_event is not None and gate_event[0] >= event_packet_index:
        raise ValueError('Gate edit was not retained before its symbolic packet')
    if intervention_event is not None and intervention_event[0] >= event_packet_index:
        raise ValueError('Intervention was not retained before its symbolic packet')

    proof = {'version': 1, 'claim': 'memory-family-oracle-evidence-v3',
        'case': {'family_id': case['family_id'], 'case_id': case['case_id'],
                 'case_sha256': case['case_sha256'], 'graph_sha256': case['graph_sha256'],
                 'profile_sha256': case['profile_sha256'], 'kind': case['kind']},
        'bindings': copy.deepcopy(bindings),
        'source': {'boundary_tick': boundary, 'application_sha256': memory.sha256(application),
                   'events_sha256': memory.sha256(source_events), 'rows_sha256': memory.sha256(source_rows),
                   'm_sha256': memory.sha256(task['m']),
                   'packets_sha256': memory.sha256(source_packets),
                   'observations_sha256': memory.sha256(source_observations),
                   'world_sha256': memory.sha256(source_actual_world)},
        'schedule': schedule,
        'post': {'events_sha256': memory.sha256(post_events), 'rows_sha256': memory.sha256(post_rows),
                 'world_state_sha256': memory.sha256(post_world),
                 'selector_sha256': memory.sha256(selector), 'u_sha256': memory.sha256(u),
                 'packets_through_decision_sha256': memory.sha256(post_packets),
                 'restored_world_sha256': memory.sha256(restored_world),
                 'decision_world_sha256': memory.sha256(after_world)},
        'trigger': trigger,
        'event': {'cue_change': None if cue_event is None else cue_event[1]['detail'],
                  'gate': None if gate_event is None else gate_event[1]['detail'],
                  'intervention': None if intervention_event is None else intervention_event[1]['change']},
        'geometry': {'before': before_geometry, 'after': after_geometry,
                     'before_occupancy': before_occupancy, 'after_occupancy': after_occupancy},
        'gold_target_ids': targets}
    memory._bounded(proof, 256 * 1024)
    return proof


def validate_oracle_evidence(proof, case, source_application, source_events, source_rows,
                             post_events, post_rows, post_world_state, bindings):
    """Reject any proof that is not the exact canonical reconstruction."""
    proof = _bounded(proof, 'oracle proof')
    expected = oracle_evidence(case, source_application, source_events, source_rows,
        post_events, post_rows, post_world_state, bindings)
    if memory.canonical_bytes(proof) != memory.canonical_bytes(expected):
        raise ValueError('Oracle proof differs from the supplied retained evidence')
    return copy.deepcopy(proof)


def selector_resource(condition, proof=None, *, case=None, source_application=None,
                      source_events=None, source_rows=None, post_events=None, post_rows=None,
                      post_world_state=None, bindings=None):
    """Expose admitted IDs/hash only to oracle; reject evidence on every other arm."""
    memory._enum(condition, CONDITIONS)
    supplied = (case, source_application, source_events, source_rows, post_events,
                post_rows, post_world_state, bindings)
    if condition != 'oracle':
        if proof is not None or any(value is not None for value in supplied):
            raise ValueError('Non-oracle selector received evaluator proof/evidence')
        return {}
    if proof is None or any(value is None for value in supplied):
        raise ValueError('Oracle selector requires its complete retained evidence')
    proof = validate_oracle_evidence(proof, *supplied)
    resource = copy.deepcopy(proof['gold_target_ids'])
    return {'resource': resource, 'resource_sha256': memory.sha256(resource),
            'provenance_sha256': memory.sha256(proof)}
