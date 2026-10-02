"""Collect declared sensor E from completed recordings, preserving source links.

No environment, selector, controller or evaluator is invoked. Admission checks
absence of engine U guidance; it cannot establish operator blindness or source
authenticity. Missing evidence never becomes an unchanged/negative check.
"""
import copy
import hashlib
import math
from pathlib import Path

from . import artifacts, memory, memory_task


MAX_RUNS = 16
MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_RESULT_BYTES = 8 * 1024 * 1024
PROTOCOL = {'version': 1, 'max_runs': MAX_RUNS, 'max_input_bytes': MAX_INPUT_BYTES,
    'max_result_bytes': MAX_RESULT_BYTES, 'max_triggers_per_episode': 1,
    'sample_rule': 'nearest-observed-else-recorded-unobserved',
    'independence_scope': 'no_engine_u_guidance', 'memory_protocol_sha256': memory.PROTOCOL_SHA256}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)
PRODUCER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
_STABLE = ('id', 'subject_id', 'kind', 'associations', 'inspection_landmark_id')
_FORBIDDEN = {'memory_u_replaced', 'application_restored', 'branch_created',
    'controller_replaced', 'replay_finished', 'replay_divergence', 'runtime_failure', 'engine_failed'}


def _renamed(run_id, kind, raw_id):
    return kind + '-' + memory.sha256([run_id, kind, raw_id])


def _bank(inspected):
    if inspected.get('facts_truncated') != 0 or inspected.get('counts', {}).get('facts') != len(inspected.get('facts', [])):
        raise ValueError('Incomplete recorded factual bank')
    facts = []
    for fact in inspected['facts']:
        fact = copy.deepcopy(fact)
        count = fact.pop('association_count', None)
        if type(count) is not int or count != len(fact.get('associations', [])):
            raise ValueError('Incomplete recorded associations')
        facts.append(fact)
    m = memory.validate_m({'version': 1, 'facts': facts})
    u = memory.validate_u(inspected.get('u'))
    if inspected.get('hashes', {}).get('m') != memory.sha256(m) or inspected['hashes'].get('u') != memory.sha256(u):
        raise ValueError('Recorded memory identity/hash mismatch')
    if u['payload']['rules']:
        raise ValueError('Acquisition used U guidance; independent collector rejects it')
    if inspected.get('active') is not None or inspected['counts'].get('requests') != 0:
        raise ValueError('Acquisition contains an inspection route')
    return m, u


def _source(run_path, remaining):
    # Preflight before exhausting the existing reader, including its chunk hashes
    # and terminal counts. The collector's smaller aggregate cap is explicit.
    run = artifacts._safe_path(run_path)
    manifest = artifacts._manifest(run)
    events = artifacts._events(run)
    paths = [run / 'recording' / name for name in ('manifest.json', 'events.jsonl')]
    for index, event in enumerate(e for e in events if e['kind'] == 'chunk'):
        if event.get('path') != f'chunks/{index:06d}.npz':
            raise ValueError('Unsafe or out-of-order chunk path')
        paths.append(run / 'recording' / event['path'])
    fingerprint = artifacts._fingerprint(paths)
    size = sum(path.stat().st_size for path in paths)
    if size > remaining:
        raise ValueError('Historical input exceeds byte limit')
    data = artifacts._load(run)
    if not data['episodes']:
        raise ValueError('Acquisition requires actual recorded ticks')
    if data['fingerprint'] != fingerprint:
        raise ValueError('Recording changed during collection')
    files = []
    for path in paths:
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        files.append({'path': str(path.relative_to(run)), 'bytes': path.stat().st_size, 'sha256': digest})
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError('Recording changed during hashing')
    if any('run_id' in event and event['run_id'] != manifest['run_id'] for event in events):
        raise ValueError('Recorded event run identity differs from manifest')
    controller = manifest.get('controller')
    if controller not in ('manual', 'teacher', 'flynn') or type(manifest.get('teacher_privileged')) is not bool or manifest['teacher_privileged'] != (controller == 'teacher'):
        raise ValueError('Missing or contradictory acquisition controller provenance')
    scenario = manifest.get('scenario')
    if (scenario.get('id') if type(scenario) is dict else scenario) != 'memory-passages':
        raise ValueError('Collector requires the declared memory-passages profile')
    if any(event['kind'] in _FORBIDDEN for event in events) or manifest.get('parent_run_id') or manifest.get('replay_mode'):
        raise ValueError('Branch, replay, replacement or failed acquisition is unsupported')
    opened = [event for event in events if event['kind'] == 'engine_opened']
    if len(opened) != 1 or opened[0].get('controller') != controller:
        raise ValueError('Missing or contradictory engine controller event')
    source = {'run_id': manifest['run_id'], 'recording_sha256': memory.sha256(files),
        'files': files, 'input_bytes': size, 'controller': controller,
        'teacher_privileged': manifest['teacher_privileged'], 'status': manifest['status'],
        'episode_outcomes': [{'episode': event.get('episode'), 'outcome': event.get('outcome')}
            for event in events if event['kind'] == 'episode_finished']}
    return data, source


def _episodes(data, source):
    manifest, events = data['manifest'], data['events']
    run_id = source['run_id']
    if sorted(data['episodes']) != list(range(len(data['episodes']))):
        raise ValueError('Acquisition requires contiguous recorded episode identities starting at zero')
    offsets, total = {}, 0
    for episode, item in sorted(data['episodes'].items()):
        offsets[episode] = total
        total += len(item['ticks'])
    frames = {(episode, tick): {'decisions': []} for episode, item in data['episodes'].items() for tick in item['ticks']}
    for event in events:
        if event['kind'] not in ('memory_sensed', 'memory_inspected', 'memory_decision'):
            continue
        if any(type(event.get(key)) is not int or event[key] < 0 for key in ('episode', 'episode_step', 'tick')):
            raise ValueError('Memory event has invalid recorded tick identity')
        key = (event['episode'], event['episode_step'])
        if key not in frames or event.get('run_id') != run_id:
            raise ValueError('Memory event lacks a matching authoritative recorded tick/run')
        if event['tick'] != offsets[event['episode']] + event['episode_step']:
            raise ValueError('Outer memory event tick differs from cumulative recorded control ticks')
        frame = frames[key]
        field = {'memory_sensed': 'sensed', 'memory_inspected': 'inspected', 'memory_decision': 'decisions'}[event['kind']]
        if field == 'decisions':
            frame[field].append(event)
        else:
            if field in frame:
                raise ValueError('Duplicate memory event at a recorded boundary')
            frame[field] = event
    result, links = [], []
    initial_u_hash = None
    last_sequence = -1
    for episode, item in sorted(data['episodes'].items()):
        if item['ticks'] != list(range(len(item['ticks']))):
            raise ValueError('Acquisition requires complete episodes starting at tick zero')
        packets, banks, triggers, observations = {}, {}, [], {}
        stable_bank = None
        for tick in item['ticks']:
            frame = frames[episode, tick]
            if 'sensed' not in frame or 'inspected' not in frame:
                raise ValueError('Missing sensor packet or complete memory inspection')
            sequence_order = [frame['sensed']['sequence'],
                *(event['sequence'] for event in frame['decisions']), frame['inspected']['sequence']]
            if sequence_order != sorted(set(sequence_order)) or sequence_order[0] <= last_sequence:
                raise ValueError('Recorded memory boundary order is invalid')
            last_sequence = sequence_order[-1]
            packet = frame['sensed']['packet']
            inspected = frame['inspected']['memory']
            m, u = _bank(inspected)
            if initial_u_hash is None:
                initial_u_hash = memory.sha256(u)
            if memory.sha256(u) != initial_u_hash:
                raise ValueError('Acquisition U identity changed')
            if packet.get('tick') != tick or packet.get('episode_id') != f'episode-{episode}' or inspected.get('tick') != tick or inspected.get('episode_id') != packet['episode_id']:
                raise ValueError('Packet/inspection episode or tick identity differs')
            memory_task._validate_packet(packet, {'episode_id': packet['episode_id'], 'm': m})
            stable = [{key: fact[key] for key in _STABLE} for fact in m['facts']]
            if stable_bank is not None and stable != stable_bank:
                raise ValueError('Candidate bank associations changed within acquisition')
            stable_bank = stable
            unknown = [{**fact, 'estimate': None, 'status': 'unknown', 'evidence': None,
                'revision': 0, 'origin': 'initial_unknown'} for fact in stable]
            initial = manifest.get('initial_memory', {})
            if initial.get('m') != memory.sha256({'version': 1, 'facts': unknown}) or initial.get('e') != memory.sha256({'version': 1, 'episodes': []}) or initial.get('u') != initial_u_hash:
                raise ValueError('Initial memory identity is missing or incompatible with acquisition')
            for sample in packet['passages']:
                if sample['id'] in observations:
                    raise ValueError('Duplicate recorded observation ID')
                observations[sample['id']] = (sample, frame['sensed']['sequence'])
            for fact in m['facts']:
                evidence = fact['evidence']
                if evidence is not None:
                    retained = observations.get(evidence['id'])
                    if retained is None or any(retained[0][key] != evidence[key] for key in ('id', 'episode_id', 'tick')) or retained[0]['subject_id'] != fact['subject_id'] or retained[0]['passability'] != fact['estimate']:
                        raise ValueError('Recorded fact lacks matching declared sensor evidence')
            expected = []
            previous = packets.get(tick - 1)
            if previous is not None:
                before_cues = {cue['id']: cue for cue in previous['cues']}
                for cue in sorted(packet['cues'], key=lambda c: c['id']):
                    before = before_cues.get(cue['id'])
                    if before is not None and before['state'] != cue['state']:
                        expected.append({'id': memory_task._sensor_id(packet['episode_id'], tick, 'trigger', cue['id']),
                            'episode_id': packet['episode_id'], 'tick': tick, 'kind': 'cue_changed',
                            'cue_id': cue['id'], 'before': before['state'], 'after': cue['state'],
                            'before_observation_id': memory_task._sensor_id(packet['episode_id'], tick - 1, 'cue', cue['id']),
                            'observation_id': memory_task._sensor_id(packet['episode_id'], tick, 'cue', cue['id'])})
            recorded, selections, bridges = [], [], []
            for event in frame['decisions']:
                detail = event.get('detail', {})
                if detail.get('tick') != tick:
                    raise ValueError('Decision tick differs from recorded boundary')
                kind = detail.get('kind')
                if kind == 'memory_trigger':
                    recorded.append(memory.validate_trigger(detail.get('trigger')))
                    triggers.append((detail['trigger'], event['sequence']))
                elif kind == 'memory_selection':
                    selection = detail.get('selection', {})
                    if selection.get('reason') != 'no_rule' or selection.get('target_ids') != []:
                        raise ValueError('Acquisition contains U targeting decisions')
                    selections.append(selection.get('event_id'))
                elif kind == 'memory_bridge':
                    bridges.append(detail)
                elif kind == 'memory_inspection':
                    raise ValueError('Acquisition contains an inspection decision')
                elif kind != 'memory_revision':
                    raise ValueError('Unknown acquisition memory decision')
            if recorded != expected or selections != [trigger['id'] for trigger in expected]:
                raise ValueError('Recorded cue trigger/selection is not reconstructible from visible packets')
            if len(bridges) != 1 or bridges[0].get('status') != 'common_goal' or bridges[0].get('landmark_id') != packet['common_goal_id']:
                raise ValueError('Acquisition route is not the declared common goal')
            visible_goal = next((landmark for landmark in packet['landmarks'] if landmark['id'] == packet['common_goal_id']), None)
            bearing = bridges[0].get('bearing')
            if visible_goal is None or type(bearing) is not list or len(bearing) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in bearing):
                raise ValueError('Common goal bridge lacks its visible declared bearing')
            expected_bearing = [math.cos(visible_goal['bearing_rad']), math.sin(visible_goal['bearing_rad'])]
            if any(not math.isclose(x, y, rel_tol=0., abs_tol=1e-12) for x, y in zip(bearing, expected_bearing)):
                raise ValueError('Common goal bridge bearing differs from visible packet')
            packets[tick], banks[tick] = packet, m
        if len(triggers) > 1:
            raise ValueError('Collector supports at most one trigger per recorded episode')
        if not triggers:
            links.append({'run_id': run_id, 'recording_sha256': source['recording_sha256'],
                'source_episode_id': f'episode-{episode}', 'recorded_episode': episode,
                'history_episode_id': None, 'gap': ['no_observed_trigger'], 'checks': []})
            continue
        trigger, sequence = triggers[0]
        history_id = f'run-{run_id}-episode-{episode}'
        history_trigger = {**trigger, 'episode_id': history_id}
        for field, kind in (('id', 'trigger'), ('cue_id', 'cue'), ('before_observation_id', 'cue-observation'), ('observation_id', 'cue-observation')):
            history_trigger[field] = _renamed(run_id, kind, trigger[field])
        checks, check_links = [], []
        used_subjects = set()
        for relation in memory.RELATIONS:
            facts = [fact for fact in banks[trigger['tick']]['facts'] if {'cue_id': trigger['cue_id'], 'relation': relation} in fact['associations']]
            if len(facts) > 1 or facts and facts[0]['subject_id'] in used_subjects:
                raise ValueError('Ambiguous relation-to-subject candidate associations')
            if not facts:
                check_links.append({'relation': relation, 'gap': ['no_candidate_association']})
                continue
            subject = facts[0]['subject_id']
            used_subjects.add(subject)
            pair, pair_links, gaps = {}, {}, []
            for phase in ('before', 'after'):
                candidates = [(sample, seq) for sample, seq in observations.values() if sample['subject_id'] == subject and
                    (sample['tick'] < trigger['tick'] if phase == 'before' else sample['tick'] >= trigger['tick'])]
                observed = [item for item in candidates if item[0]['passability'] != 'unobserved']
                candidates = observed or candidates
                if not candidates:
                    gaps.append(phase + '_missing')
                    continue
                raw, seq = (max if phase == 'before' else min)(candidates, key=lambda item: item[0]['tick'])
                if raw['passability'] == 'unobserved':
                    gaps.append(phase + '_unobserved')
                pair[phase] = {**raw, 'id': _renamed(run_id, 'observation', raw['id']),
                    'episode_id': history_id, 'subject_id': _renamed(run_id, 'subject', subject)}
                pair_links[phase] = {'observation_id': raw['id'], 'episode_id': raw['episode_id'],
                    'tick': raw['tick'], 'subject_id': subject, 'event_sequence': seq,
                    'observation_sha256': memory.sha256(raw), 'history_observation_id': pair[phase]['id']}
            if len(pair) == 2:
                checks.append({'subject_id': _renamed(run_id, 'subject', subject), 'relation': relation, **pair})
            check_links.append({'relation': relation, 'source_fact_id': facts[0]['id'],
                'source_subject_id': subject, 'gap': gaps, **pair_links})
        result.append({'id': history_id, 'trigger': history_trigger, 'checks': checks})
        links.append({'run_id': run_id, 'recording_sha256': source['recording_sha256'],
            'source_episode_id': trigger['episode_id'], 'recorded_episode': episode,
            'history_episode_id': history_id, 'trigger_id': trigger['id'], 'trigger_sequence': sequence,
            'trigger_sha256': memory.sha256(trigger), 'bank_sha256': memory.sha256(banks[trigger['tick']]),
            'before_cue_packet_sequence': frames[episode, trigger['tick'] - 1]['sensed']['sequence'],
            'after_cue_packet_sequence': frames[episode, trigger['tick']]['sensed']['sequence'], 'checks': check_links})
    return result, links


def collect_history(run_paths):
    """Return audit-linked E and fit(E), or reject unsupported/oversized records.

    Paths are completed authoritative run directories, not recording subdirs.
    This method checks local integrity, not a signed authenticity guarantee.
    """
    if type(run_paths) not in (list, tuple) or not 1 <= len(run_paths) <= MAX_RUNS:
        raise ValueError('Historical run count must be between one and sixteen')
    loaded, ids, remaining = [], set(), MAX_INPUT_BYTES
    for path in run_paths:
        data, source = _source(path, remaining)
        identity = artifacts._id(source['run_id'])
        if identity in ids:
            raise ValueError('Duplicate historical source run')
        ids.add(identity)
        remaining -= source['input_bytes']
        loaded.append((data, source))
    e, sources, links = {'version': 1, 'episodes': []}, [], []
    for data, source in sorted(loaded, key=lambda pair: pair[1]['run_id']):
        episodes, episode_links = _episodes(data, source)
        e['episodes'].extend(episodes)
        sources.append(source)
        links.extend(episode_links)
        memory.validate_e(e)  # Existing 1024-episode/4 MiB limit; never truncate.
    e = memory.validate_e(e)
    result = {'version': 1, 'acquisition': 'recorded_declared_sensor_history',
        'protocol_sha256': PROTOCOL_SHA256, 'producer_sha256': PRODUCER_SHA256,
        'e': e, 'sources': sources, 'links': links,
        'independence': {'scope': 'no_engine_u_guidance', 'checked_all_recorded_ticks': True,
            'u_guidance_used': False,
            'operator_blindness_verified': False, 'source_authenticity_verified': False},
        'history_sha256': memory.sha256(e), 'history_bytes': len(memory.canonical_bytes(e))}
    memory._bounded(result, MAX_RESULT_BYTES)
    result['u'] = memory.fit(e)  # Only E enters fitting, after evidence admission.
    result['u_payload_bytes'] = len(memory.canonical_bytes(result['u']['payload']))
    result['u_envelope_bytes'] = len(memory.canonical_bytes(result['u']))
    memory._bounded(result, MAX_RESULT_BYTES)
    if any(artifacts._fingerprint(data['paths']) != data['fingerprint'] for data, _ in loaded):
        raise ValueError('Recording changed during evidence collection or fitting')
    return result
