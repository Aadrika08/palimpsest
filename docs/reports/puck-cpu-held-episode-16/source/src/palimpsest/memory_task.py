"""Pure declared symbolic sensing and fixed reinspection; no physics or ML imports.

Only capture_symbolic receives geometry. Its caller owns agreement between
private passage inputs and the actual world. Fixture success is not embodiment.
"""

import copy
import math

from . import memory

# Retrieval reuses the existing 4 MiB E ceiling. The extra 2 KiB accommodates
# fixed selector fields/hashes; no resource is truncated to meet the cap.
MAX_SELECTOR_BYTES = memory.MAX_STATE_BYTES + 2048
ARTIFACT_CONDITIONS = ('own', 'swapped', 'sham', 'no-U', 'hand-authored')


class CueUnavailable(ValueError):
    """A required observed bearing is unavailable; the caller must stop."""


def _numbers(value, length):
    if type(value) not in (list, tuple) or len(value) != length or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError('Expected finite numeric coordinates')
    return list(value)


def _bearing(value):
    result = _numbers(value, 2)
    if not math.isclose(math.hypot(*result), 1., rel_tol=0., abs_tol=1e-12):
        raise ValueError('Bearing must be a unit vector')
    return result


def _sensor_id(episode_id, tick, channel, subject=None):
    return 'sensor-' + memory.sha256([episode_id, tick, channel, subject])


def _unique(items, key, limit):
    memory._list(items, limit)
    ids = set()
    for item in items:
        if type(item) is not dict or key not in item:
            raise ValueError('Invalid symbolic entity')
        memory._id(item[key])
        if item[key] in ids:
            raise ValueError('Duplicate symbolic entity')
        ids.add(item[key])
    return ids


def capture_symbolic(world, pose, occluders, *, episode_id, tick):
    """Project explicit private geometry into visibility-limited observations."""
    memory._id(episode_id)
    memory._int(tick)
    memory._fields(world, 'cues landmarks passages common_goal_id')
    memory._id(world['common_goal_id'])
    x, y, yaw = _numbers(pose, 3)
    if type(occluders) not in (list, tuple) or len(occluders) > memory.MAX_FACTS:
        raise ValueError('Invalid circular occluders')
    circles = [_numbers(circle, 3) for circle in occluders]
    if any(radius <= 0 for _, _, radius in circles):
        raise ValueError('Occluder radius must be positive')
    _unique(world['cues'], 'id', memory.MAX_FACTS)
    landmark_ids = _unique(world['landmarks'], 'id', memory.MAX_FACTS + 1)
    _unique(world['passages'], 'subject_id', memory.MAX_FACTS)
    if world['common_goal_id'] not in landmark_ids:
        raise ValueError('Common goal has no declared landmark')

    def visible(xy):
        px, py = _numbers(xy, 2)
        dx, dy = px - x, py - y
        distance = math.hypot(dx, dy)
        if not math.isfinite(distance):
            raise ValueError('Nonfinite geometry displacement')
        angle = math.remainder(math.atan2(dy, dx) - yaw, 2 * math.pi)
        if distance > 4. or abs(angle) > math.pi / 2:
            return None
        for ox, oy, radius in circles:
            along = 0. if not distance else max(0., min(distance, (ox - x) * dx / distance + (oy - y) * dy / distance))
            closest_x = x if not distance else x + along * dx / distance
            closest_y = y if not distance else y + along * dy / distance
            if math.hypot(ox - closest_x, oy - closest_y) <= radius:
                return None
        return angle, distance

    packet = {'version': 1, 'id': _sensor_id(episode_id, tick, 'packet'),
              'episode_id': episode_id, 'tick': tick, 'common_goal_id': world['common_goal_id'],
              'cues': [], 'landmarks': [], 'passages': []}
    for cue in sorted(world['cues'], key=lambda item: item['id']):
        memory._fields(cue, 'id xy state')
        if type(cue['state']) is not int or cue['state'] not in (0, 1):
            raise ValueError('Cue state must be zero or one')
        seen = visible(cue['xy'])
        if seen is not None:
            packet['cues'].append({'id': cue['id'], 'state': cue['state'], 'bearing_rad': seen[0]})
    seen_landmarks = {}
    for landmark in sorted(world['landmarks'], key=lambda item: item['id']):
        memory._fields(landmark, 'id xy')
        seen = visible(landmark['xy'])
        if seen is not None:
            seen_landmarks[landmark['id']] = seen
            packet['landmarks'].append({'id': landmark['id'], 'bearing_rad': seen[0]})
    for passage in sorted(world['passages'], key=lambda item: item['subject_id']):
        memory._fields(passage, 'subject_id inspection_landmark_id passability')
        memory._id(passage['inspection_landmark_id'])
        if passage['inspection_landmark_id'] not in landmark_ids:
            raise ValueError('Passage has no declared inspection landmark')
        memory._enum(passage['passability'], ('open', 'blocked'))
        seen = seen_landmarks.get(passage['inspection_landmark_id'])
        value = passage['passability'] if seen is not None and seen[1] <= .75 else 'unobserved'
        packet['passages'].append({'id': _sensor_id(episode_id, tick, 'passage', passage['subject_id']),
            'episode_id': episode_id, 'tick': tick, 'subject_id': passage['subject_id'], 'passability': value})
    return packet


def _validate_packet(packet, state):
    memory._fields(packet, 'version id episode_id tick common_goal_id cues landmarks passages')
    memory._version(packet['version'])
    memory._id(packet['episode_id'])
    memory._id(packet['common_goal_id'])
    memory._int(packet['tick'])
    if packet['episode_id'] != state['episode_id'] or packet['id'] != _sensor_id(packet['episode_id'], packet['tick'], 'packet'):
        raise ValueError('Wrong episode or invalid deterministic packet ID')
    memory._bounded(packet)
    for channel in ('cues', 'landmarks'):
        _unique(packet[channel], 'id', memory.MAX_FACTS + (channel == 'landmarks'))
        for item in packet[channel]:
            memory._fields(item, 'id state bearing_rad' if channel == 'cues' else 'id bearing_rad')
            angle = item['bearing_rad']
            if type(angle) not in (int, float) or not math.isfinite(angle) or abs(angle) > math.pi / 2:
                raise ValueError('Invalid visible bearing')
            if channel == 'cues' and (type(item['state']) is not int or item['state'] not in (0, 1)):
                raise ValueError('Invalid cue token')
    subjects = _unique(packet['passages'], 'subject_id', memory.MAX_FACTS)
    if subjects != {f['subject_id'] for f in state['m']['facts']}:
        raise ValueError('Packet passage subjects differ from the factual bank')
    for sample in packet['passages']:
        memory.validate_observation(sample)
        if sample['episode_id'] != packet['episode_id'] or sample['tick'] != packet['tick'] or sample['id'] != _sensor_id(packet['episode_id'], packet['tick'], 'passage', sample['subject_id']):
            raise ValueError('Invalid deterministic observation ID or freshness')


def initialize(m, e, u, episode_id):
    memory._id(episode_id)
    m = memory.validate_m(m)
    return {'version': 1, 'm': m, 'e': memory.validate_e(e), 'u': memory.validate_u(u),
            'initial_m': copy.deepcopy(m), 'episode_id': episode_id,
            'detector': {'tick': None, 'cues': []}, 'cursor': None,
            'requests': [], 'active': None, 'last_decisions': []}


def selector_resources(config, u):
    """Only declared per-condition resources enter the existing pure selector."""
    condition = config['condition']
    return ({'u': u} if condition in ARTIFACT_CONDITIONS else
            {'history': config['resource']} if condition == 'retrieval' else
            {'gold_target_ids': config['resource']} if condition == 'oracle' else {})


def validate_selector(config, m, u):
    """Validate a normalized copy; provenance is pinned by the run's protocol."""
    from .memory_experiment import CONDITIONS
    m, u = memory.validate_m(m), memory.validate_u(u)
    memory._fields(config, 'version condition limit resource resource_sha256 provenance_sha256')
    memory._version(config['version'])
    memory._enum(config['condition'], CONDITIONS)
    if type(config['limit']) is not int or config['limit'] != 1:
        raise ValueError('Declared baseline selector requires target budget one')
    memory._digest(config['resource_sha256'])
    memory._digest(config['provenance_sha256'])
    memory._bounded(config, MAX_SELECTOR_BYTES)
    condition, resource = config['condition'], config['resource']
    if condition == 'retrieval':
        resource = memory.validate_e(resource)
    elif condition == 'oracle':
        memory._list(resource, memory.MAX_FACTS)
        for fact_id in resource:
            memory._id(fact_id)
        if len(set(resource)) != len(resource) or not set(resource).issubset({f['id'] for f in m['facts']}):
            raise ValueError('Duplicate or dangling selector gold')
    elif resource is not None:
        raise ValueError('Condition received unsupported selector resources')
    if memory.sha256(resource) != config['resource_sha256']:
        raise ValueError('Selector resource hash differs')
    if condition not in ARTIFACT_CONDITIONS and u['payload']['rules']:
        raise ValueError('Non-artifact baseline requires empty U')
    if condition == 'no-U' and u['payload']['rules']:
        raise ValueError('No-U requires empty rules')
    if condition == 'hand-authored' and u['payload']['rules'] != [{'trigger':'cue_changed', 'relation':'local_cue'}]:
        raise ValueError('Hand-authored baseline requires its fixed local rule')
    return {**copy.deepcopy(config), 'resource': copy.deepcopy(resource)}


def configure_selector(state, config):
    """Explicit baseline configuration; never rewrite M/E/U or episodic state."""
    state = validate_state(state)
    config = validate_selector(config, state['m'], state['u'])
    return validate_state({**state, 'version':2, 'selector':config})


def validate_state(state):
    if type(state) is not dict or type(state.get('version')) is not int or state['version'] not in (1, 2):
        raise ValueError('Unsupported memory task state version')
    memory._fields(state, 'version m e u initial_m episode_id detector cursor requests active last_decisions'
                   + (' selector' if state['version'] == 2 else ''))
    memory._id(state['episode_id'])
    m, initial_m = memory.validate_m(state['m']), memory.validate_m(state['initial_m'])
    e, u = memory.validate_e(state['e']), memory.validate_u(state['u'])
    stable = ('id', 'subject_id', 'kind', 'associations', 'inspection_landmark_id')
    if [{key: f[key] for key in stable} for f in m['facts']] != [{key: f[key] for key in stable} for f in initial_m['facts']]:
        raise ValueError('Initial/current factual identity differs')
    facts = {f['id']: f for f in m['facts']}
    detector, cursor = state['detector'], state['cursor']
    memory._fields(detector, 'tick cues')
    _unique(detector['cues'], 'id', memory.MAX_FACTS)
    if cursor is None:
        if detector['tick'] is not None or detector['cues'] or state['requests'] or state['active'] is not None or state['last_decisions']:
            raise ValueError('Unstarted task contains episodic state')
    else:
        memory._fields(cursor, 'episode_id tick packet_sha256 common_goal_id bearing')
        memory._int(cursor['tick'])
        memory._id(cursor['common_goal_id'])
        memory._digest(cursor['packet_sha256'])
        _bearing(cursor['bearing'])
        if cursor['episode_id'] != state['episode_id'] or type(detector['tick']) is not int or detector['tick'] != cursor['tick']:
            raise ValueError('Detector/cursor episode or tick differs')
        for fact in facts.values():
            evidence = fact['evidence']
            if evidence is not None and evidence['episode_id'] == state['episode_id'] and evidence['tick'] > cursor['tick']:
                raise ValueError('Task contains future evidence')
    for cue in detector['cues']:
        memory._fields(cue, 'id state observation_id')
        if type(cue['state']) is not int or cue['state'] not in (0, 1) or cue['observation_id'] != _sensor_id(state['episode_id'], detector['tick'], 'cue', cue['id']):
            raise ValueError('Invalid retained cue observation')
    memory._list(state['requests'], memory.MAX_FACTS)
    pending_ids = set()
    for request in state['requests'] + ([] if state['active'] is None else [state['active']]):
        active = request is state['active']
        memory._fields(request, 'event_id fact_id requested_tick started_tick deadline_tick' if active else 'event_id fact_id requested_tick')
        memory._id(request['event_id'])
        memory._id(request['fact_id'])
        memory._int(request['requested_tick'])
        if request['fact_id'] not in facts or request['fact_id'] in pending_ids or cursor is None or request['requested_tick'] > cursor['tick']:
            raise ValueError('Duplicate, dangling or future inspection request')
        pending_ids.add(request['fact_id'])
        if active:
            memory._int(request['started_tick'])
            memory._int(request['deadline_tick'])
            if not request['requested_tick'] <= request['started_tick'] <= cursor['tick'] < request['deadline_tick'] or request['deadline_tick'] != request['started_tick'] + 200:
                raise ValueError('Invalid active inspection deadline')
    if state['requests'] != sorted(state['requests'], key=lambda r: (r['requested_tick'], r['fact_id'])):
        raise ValueError('Noncanonical inspection request order')
    memory._list(state['last_decisions'], 8)
    memory._bounded(state['last_decisions'], 16384)
    for item in state['last_decisions']:
        memory._fields(item, 'kind tick event_id fact_id status target_ids landmark_id bearing')
        memory._enum(item['kind'], ('memory_trigger', 'memory_selection', 'memory_revision', 'memory_inspection', 'memory_bridge'))
        memory._int(item['tick'])
        if cursor is None or item['tick'] > cursor['tick']:
            raise ValueError('Future memory decision')
        for field in ('event_id', 'fact_id', 'status', 'landmark_id'):
            if item[field] is not None:
                memory._id(item[field])
        memory._list(item['target_ids'], memory.MAX_TARGETS)
        for target in item['target_ids']:
            memory._id(target)
        if any(target not in facts for target in item['target_ids']) or (item['fact_id'] is not None and item['fact_id'] not in facts):
            raise ValueError('Dangling decision fact')
        if item['bearing'] is not None:
            _bearing(item['bearing'])
    normalized = {**copy.deepcopy(state), 'm': m, 'initial_m': initial_m, 'e': e, 'u': u}
    if state['version'] == 2:
        normalized['selector'] = validate_selector(state['selector'], m, u)
    return normalized


def reset(state, episode_id):
    state = validate_state(state)
    result = initialize(state['initial_m'], state['e'], state['u'], episode_id)
    return configure_selector(result, state['selector']) if state['version'] == 2 else result


def _summary(event):
    revision = event.get('revision', {})
    selection = event.get('selection', {})
    trigger = event.get('trigger', {})
    return {'kind': event['kind'], 'tick': event['tick'],
            'event_id': event.get('event_id', revision.get('event_id', selection.get('event_id', trigger.get('id')))),
            'fact_id': event.get('fact_id', revision.get('fact_id')),
            'status': event.get('status', revision.get('reason', selection.get('reason'))),
            'target_ids': selection.get('target_ids', []),
            'landmark_id': event.get('landmark_id'), 'bearing': event.get('bearing')}


def advance_memory(state, packet):
    """Pure one-boundary update; duplicate packets retain their effective cue."""
    state = validate_state(state)
    _validate_packet(packet, state)
    tick, episode_id = packet['tick'], state['episode_id']
    digest = memory.sha256(packet)
    cursor = state['cursor']
    if cursor is not None:
        if packet['common_goal_id'] != cursor['common_goal_id']:
            raise ValueError('Common goal identity changed within an episode')
        if tick == cursor['tick']:
            if digest != cursor['packet_sha256']:
                raise ValueError('Packet boundary reused with different content')
            return state, cursor['bearing'].copy(), []
    expected = 0 if cursor is None else cursor['tick'] + 1
    if tick != expected:
        raise ValueError('Stale or future packet; consecutive control ticks required')
    audit, new_requests = [], []
    previous = {c['id']: c for c in state['detector']['cues']}
    triggers = []
    if state['detector']['tick'] == tick - 1:
        for cue in sorted(packet['cues'], key=lambda c: c['id']):
            before = previous.get(cue['id'])
            if before is not None and before['state'] != cue['state']:
                triggers.append({'id': _sensor_id(episode_id, tick, 'trigger', cue['id']),
                    'episode_id': episode_id, 'tick': tick, 'kind': 'cue_changed',
                    'cue_id': cue['id'], 'before': before['state'], 'after': cue['state'],
                    'before_observation_id': before['observation_id'],
                    'observation_id': _sensor_id(episode_id, tick, 'cue', cue['id'])})
    for trigger in triggers:
        if state['version'] == 1:
            selection = memory.select(state['m'], trigger, state['u'])
        else:
            from .memory_experiment import selection_for_condition
            config = state['selector']
            selection = selection_for_condition(config['condition'], state['m'], trigger,
                limit=config['limit'], **selector_resources(config, state['u']))
        audit.extend([{'kind': 'memory_trigger', 'tick': tick, 'trigger': trigger},
                      {'kind': 'memory_selection', 'tick': tick, 'selection': selection}])
        state['m'], revisions, requests = memory.revise(state['m'], trigger, selection, [], episode_id=episode_id, tick=tick)
        audit.extend({'kind': 'memory_revision', 'tick': tick, 'revision': r} for r in revisions)
        new_requests.extend(requests)
    state['m'], revisions, _ = memory.revise(state['m'], None,
        {'event_id': None, 'target_ids': [], 'reason': 'no_rule'}, packet['passages'], episode_id=episode_id, tick=tick)
    audit.extend({'kind': 'memory_revision', 'tick': tick, 'revision': r} for r in revisions)
    facts = {f['id']: f for f in state['m']['facts']}

    def resolved(fact_id):
        fact = facts[fact_id]
        return fact['status'] == 'observed' and fact['evidence']['episode_id'] == episode_id and fact['evidence']['tick'] == tick

    active = state['active']
    existing = {r['fact_id'] for r in state['requests']} | (set() if active is None else {active['fact_id']})
    for request in new_requests:
        if request['fact_id'] not in existing and not resolved(request['fact_id']):
            state['requests'].append(request)
            existing.add(request['fact_id'])
            audit.append({'kind': 'memory_inspection', 'tick': tick, **request, 'status': 'requested'})
    state['requests'] = sorted((r for r in state['requests'] if not resolved(r['fact_id'])),
                               key=lambda r: (r['requested_tick'], r['fact_id']))
    timed_out = False
    if active is not None and (resolved(active['fact_id']) or tick >= active['deadline_tick']):
        timed_out = not resolved(active['fact_id'])
        audit.append({'kind': 'memory_inspection', 'tick': tick, 'event_id': active['event_id'],
                      'fact_id': active['fact_id'], 'status': 'timeout' if timed_out else 'resolved'})
        active = None
    landmarks = {item['id']: item['bearing_rad'] for item in packet['landmarks']}
    if active is None and not timed_out:
        for request in state['requests']:
            if facts[request['fact_id']]['inspection_landmark_id'] in landmarks:
                active = {**request, 'started_tick': tick, 'deadline_tick': tick + 200}
                state['requests'].remove(request)
                audit.append({'kind': 'memory_inspection', 'tick': tick, **request, 'status': 'started'})
                break
    goal = packet['common_goal_id'] if active is None else facts[active['fact_id']]['inspection_landmark_id']
    if goal not in landmarks:
        raise CueUnavailable('goal_cue_unavailable: ' + goal)
    angle = landmarks[goal]
    bearing = [math.cos(angle), math.sin(angle)]
    audit.append({'kind': 'memory_bridge', 'tick': tick, 'landmark_id': goal,
                  'status': 'common_goal' if active is None else 'inspection', 'bearing': bearing.copy()})
    state['active'] = active
    state['detector'] = {'tick': tick, 'cues': [{'id': c['id'], 'state': c['state'],
        'observation_id': _sensor_id(episode_id, tick, 'cue', c['id'])}
        for c in sorted(packet['cues'], key=lambda c: c['id'])]}
    state['cursor'] = {'episode_id': episode_id, 'tick': tick, 'packet_sha256': digest,
                       'common_goal_id': packet['common_goal_id'], 'bearing': bearing.copy()}
    state['last_decisions'] = (state['last_decisions'] + [_summary(item) for item in audit])[-8:]
    return state, bearing, audit


def inspect(state):
    state = validate_state(state)
    facts = [{**fact, 'associations': fact['associations'][:8],
              'association_count': len(fact['associations'])} for fact in state['m']['facts'][:16]]
    result = {'version': 1, 'episode_id': state['episode_id'],
            'tick': None if state['cursor'] is None else state['cursor']['tick'],
            'hashes': {key: memory.sha256(state[key]) for key in ('m', 'e', 'u')},
            'counts': {'facts': len(state['m']['facts']), 'episodes': len(state['e']['episodes']),
                       'requests': len(state['requests']) + (state['active'] is not None)},
            'u': state['u'], 'facts': facts, 'facts_truncated': max(0, len(state['m']['facts']) - 16),
            'active': state['active'], 'recent_decisions': state['last_decisions']}
    if state['version'] == 2:
        config = state['selector']
        result['selector'] = {key: config[key] for key in config if key != 'resource'}
        result['selector']['resource_bytes'] = len(memory.canonical_bytes(config['resource']))
        result['selector']['configuration_sha256'] = memory.sha256(config)
    return result
