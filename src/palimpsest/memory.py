"""Bounded artificial revision memory; no world/controller/evaluator access.

Validation establishes structure, not observational truth. Use seed_m with the
retained sensor observations to initialize known facts. The owning task keeps
the ingestion cursor and cross-call ID registry; these operations are pure.
M and E each have a 4 MiB serialized ceiling so candidate association lists
cannot defeat their record-count limits. Oversized inputs fail, never truncate.
"""

import copy
import hashlib
import json
from pathlib import Path


RELATIONS = ('local_cue', 'paired_cue')
MAX_FACTS, MAX_EPISODES, MAX_TARGETS = 256, 1024, 8
MAX_STATE_BYTES = 4 * 1024 * 1024
MAX_PAYLOAD_BYTES, MAX_ARTIFACT_BYTES = 4096, 8192
PROTOCOL = {'version': 1, 'vocabulary': 'passage-relations-v1',
            'minimum_checks_per_relation': 4, 'changed_rate_numerator': 3,
            'other_rate_numerator': 1, 'rate_denominator': 4,
            'max_facts': MAX_FACTS, 'max_episodes': MAX_EPISODES,
            'max_targets': MAX_TARGETS, 'default_targets': 1,
            'max_state_bytes': MAX_STATE_BYTES, 'max_rules': 4,
            'max_payload_bytes': MAX_PAYLOAD_BYTES, 'max_artifact_bytes': MAX_ARTIFACT_BYTES}


def canonical_bytes(value):
    """Canonical UTF-8 JSON; reject non-JSON values and nonfinite numbers."""
    def plain(item, depth=0):
        if depth > 32:
            raise ValueError('Memory JSON nesting exceeds limit')
        if item is None or type(item) in (str, int, bool, float):
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                plain(child, depth + 1)
        elif type(item) is list:
            for child in item:
                plain(child, depth + 1)
        else:
            raise ValueError('Memory state requires plain JSON values')
    plain(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError('Invalid memory JSON') from exc


def sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


PROTOCOL_SHA256 = sha256(PROTOCOL)
PRODUCER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _fields(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise ValueError('Missing or unknown memory fields')


def _id(value):
    if type(value) is not str or not value or len(value) > 128:
        raise ValueError('Invalid memory ID')


def _int(value):
    if type(value) is not int or value < 0:
        raise ValueError('Expected nonnegative memory integer')


def _enum(value, choices):
    if type(value) is not str or value not in choices:
        raise ValueError('Unknown memory enum')


def _digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Invalid SHA256')


def _list(value, cap):
    if type(value) is not list or len(value) > cap:
        raise ValueError('Memory list exceeds limit or has wrong type')


def _bounded(value, cap=MAX_STATE_BYTES):
    if len(canonical_bytes(value)) > cap:
        raise ValueError('Memory JSON exceeds byte limit')


def _version(value):
    if type(value) is not int or value != 1:
        raise ValueError('Unsupported memory schema version')


def validate_observation(observation):
    _fields(observation, 'id episode_id tick subject_id passability')
    for key in ('id', 'episode_id', 'subject_id'):
        _id(observation[key])
    _int(observation['tick'])
    _enum(observation['passability'], ('open', 'blocked', 'unobserved'))
    return copy.deepcopy(observation)


def validate_trigger(trigger):
    _fields(trigger, 'id episode_id tick kind cue_id before after before_observation_id observation_id')
    for key in ('id', 'episode_id', 'cue_id', 'before_observation_id', 'observation_id'):
        _id(trigger[key])
    _int(trigger['tick'])
    _enum(trigger['kind'], ('cue_changed',))
    if any(type(trigger[key]) is not int or trigger[key] not in (0, 1) for key in ('before', 'after')):
        raise ValueError('Cue tokens require zero or one integers')
    if trigger['before'] == trigger['after'] or trigger['before_observation_id'] == trigger['observation_id']:
        raise ValueError('Trigger requires distinct observed cue states')
    return copy.deepcopy(trigger)


def validate_m(m):
    _fields(m, 'version facts')
    _version(m['version'])
    _list(m['facts'], MAX_FACTS)
    _bounded(m)
    result = copy.deepcopy(m)
    ids, subjects, evidence_ids = set(), set(), set()
    for fact in result['facts']:
        _fields(fact, 'id subject_id kind estimate status associations inspection_landmark_id evidence revision origin')
        for key in ('id', 'subject_id', 'inspection_landmark_id'):
            _id(fact[key])
        if fact['id'] in ids or fact['subject_id'] in subjects:
            raise ValueError('Duplicate fact ID or subject')
        ids.add(fact['id'])
        subjects.add(fact['subject_id'])
        _enum(fact['kind'], ('passability',))
        _enum(fact['status'], ('unknown', 'observed', 'uncertain'))
        _enum(fact['origin'], ('observed', 'initial_unknown'))
        _int(fact['revision'])
        if fact['estimate'] is not None:
            _enum(fact['estimate'], ('open', 'blocked'))
        evidence = fact['evidence']
        if evidence is not None:
            _fields(evidence, 'id episode_id tick')
            _id(evidence['id'])
            _id(evidence['episode_id'])
            _int(evidence['tick'])
            if evidence['id'] in evidence_ids:
                raise ValueError('Duplicate fact evidence ID')
            evidence_ids.add(evidence['id'])
        known = fact['estimate'] is not None
        if known != (evidence is not None) or fact['origin'] != ('observed' if known else 'initial_unknown'):
            raise ValueError('Fact estimate requires retained observed evidence')
        if fact['status'] == 'unknown' and known or fact['status'] == 'observed' and not known:
            raise ValueError('Fact certainty requires an observed estimate')
        _list(fact['associations'], MAX_STATE_BYTES)
        pairs = set()
        for association in fact['associations']:
            _fields(association, 'cue_id relation')
            _id(association['cue_id'])
            _enum(association['relation'], RELATIONS)
            pair = (association['cue_id'], association['relation'])
            if pair in pairs:
                raise ValueError('Duplicate candidate association')
            pairs.add(pair)
        fact['associations'].sort(key=lambda a: (a['cue_id'], a['relation']))
    result['facts'].sort(key=lambda f: f['id'])
    return result


def _observations(observations):
    _list(observations, MAX_STATE_BYTES)
    _bounded(observations)
    by_id = {}
    for item in observations:
        item = validate_observation(item)
        if item['id'] in by_id and by_id[item['id']] != item:
            raise ValueError('Observation ID reused with different content')
        by_id[item['id']] = item
    return list(by_id.values())


def seed_m(facts, observations):
    """Initialize facts using retained declared samples, never simulator truth."""
    m = validate_m({'version': 1, 'facts': facts})
    samples = {item['id']: item for item in _observations(observations)}
    for fact in m['facts']:
        evidence = fact['evidence']
        if evidence is not None:
            sample = samples.get(evidence['id'])
            if sample is None or any(sample[k] != evidence[k] for k in ('id', 'episode_id', 'tick')) or sample['subject_id'] != fact['subject_id'] or sample['passability'] != fact['estimate']:
                raise ValueError('Seed fact lacks matching retained observation')
            if any(other['episode_id'] == sample['episode_id'] and other['tick'] == sample['tick'] and other['subject_id'] == sample['subject_id'] and other['passability'] not in ('unobserved', sample['passability']) for other in samples.values()):
                raise ValueError('Conflicted observations cannot seed a known fact')
    return m


def validate_e(e):
    _fields(e, 'version episodes')
    _version(e['version'])
    _list(e['episodes'], MAX_EPISODES)
    _bounded(e)
    result = copy.deepcopy(e)
    ids, observation_ids, trigger_ids = set(), set(), set()
    for episode in result['episodes']:
        _fields(episode, 'id trigger checks')
        _id(episode['id'])
        trigger = validate_trigger(episode['trigger'])
        if episode['id'] in ids or trigger['id'] in trigger_ids or trigger['episode_id'] != episode['id']:
            raise ValueError('Duplicate or mismatched historical episode/trigger')
        ids.add(episode['id'])
        trigger_ids.add(trigger['id'])
        _list(episode['checks'], len(RELATIONS))
        relations = set()
        for check in episode['checks']:
            _fields(check, 'subject_id relation before after')
            _id(check['subject_id'])
            _enum(check['relation'], RELATIONS)
            if check['relation'] in relations:
                raise ValueError('Duplicate checked relation')
            relations.add(check['relation'])
            before, after = (validate_observation(check[k]) for k in ('before', 'after'))
            for sample in (before, after):
                if sample['subject_id'] != check['subject_id'] or sample['episode_id'] != episode['id'] or sample['id'] in observation_ids:
                    raise ValueError('Duplicate or dangling historical observation')
                observation_ids.add(sample['id'])
            if not before['tick'] < trigger['tick'] <= after['tick']:
                raise ValueError('Invalid historical evidence ordering')
    return result


def validate_u(u):
    _fields(u, 'payload provenance payload_sha256')
    _bounded(u, MAX_ARTIFACT_BYTES)
    payload, provenance = u['payload'], u['provenance']
    _fields(payload, 'version vocabulary rules')
    _version(payload['version'])
    _enum(payload['vocabulary'], ('passage-relations-v1',))
    _list(payload['rules'], 4)
    _bounded(payload, MAX_PAYLOAD_BYTES)
    triggers = set()
    for rule in payload['rules']:
        _fields(rule, 'trigger relation')
        _enum(rule['trigger'], ('cue_changed',))
        _enum(rule['relation'], RELATIONS)
        if rule['trigger'] in triggers:
            raise ValueError('Duplicate/conflicting trigger rules')
        triggers.add(rule['trigger'])
    _fields(provenance, 'method history_sha256 protocol_sha256 producer_sha256 support')
    _enum(provenance['method'], ('history-fit-v1', 'hand-authored-v1', 'empty-v1'))
    for key in ('protocol_sha256', 'producer_sha256'):
        _digest(provenance[key])
    if provenance['history_sha256'] is not None:
        _digest(provenance['history_sha256'])
    if provenance['method'] == 'history-fit-v1' and provenance['history_sha256'] is None:
        raise ValueError('Fitted rule requires history provenance')
    if provenance['method'] == 'empty-v1' and payload['rules']:
        raise ValueError('Empty artifact cannot contain a rule')
    _fields(provenance['support'], 'local_cue paired_cue')
    for counts in provenance['support'].values():
        _fields(counts, 'observed changed')
        _int(counts['observed'])
        _int(counts['changed'])
        if counts['changed'] > counts['observed'] or counts['observed'] > MAX_EPISODES:
            raise ValueError('Invalid historical support counts')
    _digest(u['payload_sha256'])
    if sha256(payload) != u['payload_sha256']:
        raise ValueError('U payload hash mismatch')
    return copy.deepcopy(u)


def artifact(relation=None, *, method='hand-authored-v1', history_sha256=None, support=None):
    payload = {'version': 1, 'vocabulary': 'passage-relations-v1',
               'rules': [] if relation is None else [{'trigger': 'cue_changed', 'relation': relation}]}
    return validate_u({'payload': payload, 'payload_sha256': sha256(payload),
        'provenance': {'method': method, 'history_sha256': history_sha256,
            'protocol_sha256': PROTOCOL_SHA256,
            'producer_sha256': PRODUCER_SHA256,
            'support': {r: {'observed': 0, 'changed': 0} for r in RELATIONS} if support is None else support}})


def fit(e):
    """Fit only past observed episode checks; insufficient/ambiguous E abstains."""
    e = validate_e(e)
    support = {r: {'observed': 0, 'changed': 0} for r in RELATIONS}
    for episode in e['episodes']:
        values = {}
        for check in episode['checks']:
            for sample in (check['before'], check['after']):
                if sample['passability'] != 'unobserved':
                    values.setdefault((sample['subject_id'], sample['tick']), set()).add(sample['passability'])
        for check in episode['checks']:
            before, after = check['before'], check['after']
            if any(sample['passability'] == 'unobserved' or len(values.get((sample['subject_id'], sample['tick']), ())) != 1 for sample in (before, after)):
                continue
            counts = support[check['relation']]
            counts['observed'] += 1
            counts['changed'] += before['passability'] != after['passability']
    relation = None
    if all(counts['observed'] >= 4 for counts in support.values()):
        for candidate in RELATIONS:
            own = support[candidate]
            other = support[RELATIONS[1 - RELATIONS.index(candidate)]]
            if 4 * own['changed'] >= 3 * own['observed'] and 4 * other['changed'] <= other['observed']:
                relation = candidate
    return artifact(relation, method='history-fit-v1', history_sha256=sha256(e), support=support)


def validate_selection(selection, m, trigger=None):
    _fields(selection, 'event_id target_ids reason')
    m = validate_m(m)
    if trigger is not None:
        trigger = validate_trigger(trigger)
    if selection['event_id'] is not None:
        _id(selection['event_id'])
    _enum(selection['reason'], ('matched', 'no_rule', 'no_match', 'budget'))
    _list(selection['target_ids'], MAX_TARGETS)
    for target in selection['target_ids']:
        _id(target)
    targets = selection['target_ids']
    if len(set(targets)) != len(targets) or not set(targets).issubset({f['id'] for f in m['facts']}):
        raise ValueError('Duplicate or dangling selection target')
    if selection['event_id'] != (None if trigger is None else trigger['id']) or targets and (trigger is None or selection['reason'] in ('no_rule', 'no_match')):
        raise ValueError('Selection requires its matching trigger')
    result = copy.deepcopy(selection)
    result['target_ids'].sort()
    return result


def select(m, trigger, u, *, limit=1):
    m, trigger, u = validate_m(m), validate_trigger(trigger), validate_u(u)
    _int(limit)
    if limit > MAX_TARGETS:
        raise ValueError('Selection budget exceeds eight')
    rules = u['payload']['rules']
    targets = [] if not rules else [f['id'] for f in m['facts'] if
        {'cue_id': trigger['cue_id'], 'relation': rules[0]['relation']} in f['associations']]
    reason = 'no_rule' if not rules else 'no_match' if not targets else 'budget' if len(targets) > limit else 'matched'
    return {'event_id': trigger['id'], 'target_ids': targets[:limit], 'reason': reason}


def revise(m, trigger, selection, observations, *, episode_id, tick):
    """Reconsider then assimilate; owner deduplicates trigger/request ingestion."""
    m = validate_m(m)
    trigger = None if trigger is None else validate_trigger(trigger)
    selection = validate_selection(selection, m, trigger)
    _id(episode_id)
    _int(tick)
    samples = _observations(observations)
    if trigger is not None and (trigger['episode_id'] != episode_id or trigger['tick'] > tick):
        raise ValueError('Future or wrong-episode trigger')
    facts = {f['id']: f for f in m['facts']}
    subjects = {f['subject_id']: f for f in m['facts']}
    if any(f['evidence'] is not None and f['evidence']['episode_id'] == episode_id and
           f['evidence']['tick'] > tick for f in m['facts']):
        raise ValueError('Current bank contains future evidence')
    grouped = {}
    for sample in samples:
        if sample['episode_id'] != episode_id or sample['tick'] > tick:
            raise ValueError('Future or wrong-episode observation')
        if sample['subject_id'] not in subjects:
            raise ValueError('Observation has dangling subject')
        fact = subjects[sample['subject_id']]
        evidence = fact['evidence']
        if evidence is not None and sample['id'] == evidence['id'] and (sample['episode_id'] != evidence['episode_id'] or sample['tick'] != evidence['tick'] or sample['passability'] != fact['estimate']):
            raise ValueError('Observation ID reused with different content')
        if sample['tick'] == tick and sample['passability'] != 'unobserved':
            grouped.setdefault(sample['subject_id'], []).append(sample)
    events, requests = [], []
    def record(fact, before, reason, evidence_ids):
        if (fact['estimate'], fact['status']) != (before['estimate'], before['status']):
            fact['revision'] += 1
        if fact != before or reason == 'conflict':
            events.append({'fact_id': fact['id'], 'event_id': None if trigger is None else trigger['id'],
                'tick': tick, 'before': before, 'after': copy.deepcopy(fact),
                'evidence_ids': sorted(evidence_ids), 'reason': reason})
    if trigger is not None and trigger['tick'] == tick:
        for target in selection['target_ids']:
            fact = facts[target]
            evidence = fact['evidence']
            if evidence is not None and evidence['episode_id'] == episode_id and evidence['tick'] >= trigger['tick']:
                continue
            if fact['status'] != 'uncertain':
                before = copy.deepcopy(fact)
                fact['status'] = 'uncertain'
                record(fact, before, 'reconsider', [trigger['observation_id']])
            requests.append({'event_id': trigger['id'], 'fact_id': target, 'requested_tick': tick})
    for subject, checks in sorted(grouped.items()):
        fact = subjects[subject]
        before = copy.deepcopy(fact)
        evidence = fact['evidence']
        if evidence is not None and evidence['episode_id'] == episode_id and evidence['tick'] == tick and evidence['id'] not in {sample['id'] for sample in checks}:
            checks.append({**evidence, 'subject_id': subject, 'passability': fact['estimate']})
        if len({sample['passability'] for sample in checks}) > 1:
            fact['status'] = 'uncertain'
            record(fact, before, 'conflict', [sample['id'] for sample in checks])
        else:
            sample = min(checks, key=lambda s: s['id'])
            fact.update(estimate=sample['passability'], status='observed', origin='observed',
                        evidence={k: sample[k] for k in ('id', 'episode_id', 'tick')})
            record(fact, before, 'direct_observation', [item['id'] for item in checks])
            requests = [request for request in requests if request['fact_id'] != fact['id']]
    return validate_m(m), events, requests
