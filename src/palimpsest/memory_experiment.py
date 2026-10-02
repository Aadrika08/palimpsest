"""Synthetic DEVELOPMENT targeting fixtures and nine bounded baselines.

No physics is run and no histories are physically acquired. Generation obtains
gold from retained geometry/occupancy changes, independently of U/fit/select.
Only the evaluator comparison receives private truth; fit receives E alone.
Held-out splits are deliberately unavailable until a separate protocol freeze.
"""

import copy
import hashlib
from pathlib import Path

from . import memory, memory_world


SPLITS = ('development-history', 'development-test')
KINDS = ('change', 'null', 'no-event')
CONDITIONS = ('own', 'swapped', 'sham', 'no-U', 'hand-authored',
              'history-independent', 'traversal', 'retrieval', 'oracle')
MAX_CASE_BYTES = 64 * 1024
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PROTOCOL = {'version': 1, 'claim': 'synthetic-development-only',
    'splits': list(SPLITS), 'kinds': list(KINDS), 'conditions': list(CONDITIONS),
    'memory_protocol_sha256': memory.PROTOCOL_SHA256,
    'world_profile_sha256': memory_world.PROFILE_SHA256,
    'default_history_episodes': 4, 'default_target_limit': 1,
    'before_tick': 1, 'trigger_tick': 2, 'after_tick': 3,
    'counterbalance': 'seed-bit0-relation-side-bit1-fact-order-bit2-subject-order',
    'retrieval': 'latest-complete-matching-episode-exactly-one-changed-relation',
    'max_case_bytes': MAX_CASE_BYTES}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def _integer(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid bounded development integer')


def _fields(value, names):
    if type(value) is not dict or set(value) != set(names.split()):
        raise ValueError('Missing or unknown development fixture fields')
    if len(memory.canonical_bytes(value)) > MAX_CASE_BYTES:
        raise ValueError('Development fixture exceeds byte limit')


def _sample(case_id, subject, value, tick):
    return {'id': f'{subject}-observation-{tick}', 'episode_id': case_id,
            'tick': tick, 'subject_id': subject, 'passability': value}


def _layout(seed, regime, split, kind):
    """Fixed counterbalancing and gate mechanism, independent of fitted rules."""
    case_id = f'{split}-{seed:08x}'
    relations = list(memory.RELATIONS[::(-1 if seed & 1 else 1)])
    letters = ['z', 'a'] if seed & 2 else ['a', 'z']
    subject_letters = ['z', 'a'] if seed & 4 else ['a', 'z']
    subjects = [f'{case_id}-subject-{letter}' for letter in subject_letters]
    before = [[*xy, memory_world.OBSTACLE_RADIUS] for xy in memory_world.validate_layout()]
    after = copy.deepcopy(before)
    if kind == 'change':
        side = relations.index(regime)
        after[side + 3][:2] = memory_world.CLOSED_GATES[side]
    return case_id, relations, letters, subjects, before, after


def _trigger(case_id, kind):
    return None if kind == 'no-event' else {'id': f'{case_id}-trigger',
        'episode_id': case_id, 'tick': 2, 'kind': 'cue_changed', 'cue_id': f'{case_id}-cue',
        'before': 0, 'after': 1, 'before_observation_id': f'{case_id}-cue-observation-1',
        'observation_id': f'{case_id}-cue-observation-2'}


def gold_target_ids(m, before_occupancy, after_occupancy, trigger):
    """Evaluator-only stale previously observed expectations, never unknowns."""
    m = memory.validate_m(m)
    subjects = {fact['subject_id'] for fact in m['facts']}
    for occupancy in (before_occupancy, after_occupancy):
        if type(occupancy) is not dict or set(occupancy) != subjects or any(type(v) is not str or v not in ('open', 'blocked') for v in occupancy.values()):
            raise ValueError('Occupancy must cover exactly the factual subjects')
    if trigger is None:
        return []
    trigger = memory.validate_trigger(trigger)
    return sorted(fact['id'] for fact in m['facts'] if fact['status'] == 'observed'
        and fact['estimate'] == before_occupancy[fact['subject_id']]
        and before_occupancy[fact['subject_id']] != after_occupancy[fact['subject_id']]
        and (fact['evidence']['episode_id'] != trigger['episode_id'] or fact['evidence']['tick'] < trigger['tick']))


def make_case(seed, regime, split, *, kind='change'):
    """Return separately public bank/event and private synthetic evaluator truth."""
    _integer(seed, 2**32 - 1)
    if regime not in memory.RELATIONS or split not in SPLITS or kind not in KINDS:
        raise ValueError('Unknown development regime/split/kind; held-out is not enabled')
    case_id, relations, letters, subjects, before_geometry, after_geometry = _layout(seed, regime, split, kind)
    before_labels = memory_world.passage_status(before_geometry)
    after_labels = memory_world.passage_status(after_geometry)
    before_occupancy = {subject: before_labels[side_id] for subject, side_id in zip(subjects, memory_world.SUBJECTS)}
    after_occupancy = {subject: after_labels[side_id] for subject, side_id in zip(subjects, memory_world.SUBJECTS)}
    retained_before = [_sample(case_id, subject, before_occupancy[subject], 1) for subject in subjects]
    retained_after = [_sample(case_id, subject, after_occupancy[subject], 3) for subject in subjects]
    cue_id = f'{case_id}-cue'
    facts = []
    for side, sample in enumerate(retained_before):
        facts.append({'id': f'{case_id}-fact-{letters[side]}', 'subject_id': sample['subject_id'],
            'kind': 'passability', 'estimate': sample['passability'], 'status': 'observed',
            'associations': [{'cue_id': cue_id, 'relation': relations[side]}],
            'inspection_landmark_id': f'{sample["subject_id"]}-inspection',
            'evidence': {k: sample[k] for k in ('id', 'episode_id', 'tick')},
            'revision': 0, 'origin': 'observed'})
    m = memory.seed_m(facts, retained_before)
    trigger = _trigger(case_id, kind)
    fixture = {'version': 1, 'claim': 'synthetic-development-fixture', 'case_id': case_id,
        'split': split, 'protocol_sha256': PROTOCOL_SHA256, 'source_sha256': SOURCE_SHA256,
        'm': m, 'trigger': trigger, 'before_observations': retained_before}
    truth = {'version': 1, 'claim': 'synthetic-evaluator-truth', 'case_id': case_id,
        'protocol_sha256': PROTOCOL_SHA256, 'source_sha256': SOURCE_SHA256,
        'seed': seed, 'regime': regime, 'kind': kind, 'subjects_by_side': subjects,
        'before_geometry': before_geometry, 'after_geometry': after_geometry,
        'before_occupancy': before_occupancy, 'after_occupancy': after_occupancy,
        'after_observations': retained_after,
        'gold_target_ids': gold_target_ids(m, before_occupancy, after_occupancy, trigger)}
    return validate_fixture(fixture), validate_truth(truth, fixture)


def validate_fixture(fixture):
    _fields(fixture, 'version claim case_id split protocol_sha256 source_sha256 m trigger before_observations')
    if type(fixture['version']) is not int or fixture['version'] != 1 or fixture['claim'] != 'synthetic-development-fixture' or fixture['split'] not in SPLITS:
        raise ValueError('Unsupported synthetic development fixture')
    if fixture['protocol_sha256'] != PROTOCOL_SHA256 or fixture['source_sha256'] != SOURCE_SHA256:
        raise ValueError('Development fixture source/protocol mismatch')
    if type(fixture['case_id']) is not str or not fixture['case_id'].startswith(fixture['split'] + '-') or len(fixture['case_id']) > 128:
        raise ValueError('Invalid development case ID')
    result = copy.deepcopy(fixture)
    result['m'] = memory.validate_m(result['m'])
    if len(result['m']['facts']) != 2 or type(result['before_observations']) is not list or len(result['before_observations']) != 2:
        raise ValueError('Development case needs exactly two retained passage samples/facts')
    result['before_observations'] = [memory.validate_observation(o) for o in result['before_observations']]
    if len({sample['id'] for sample in result['before_observations']}) != 2 or any(sample['episode_id'] != result['case_id'] or sample['tick'] != 1 for sample in result['before_observations']):
        raise ValueError('Invalid retained synthetic before observations')
    memory.seed_m(result['m']['facts'], result['before_observations'])
    if result['trigger'] is not None:
        result['trigger'] = memory.validate_trigger(result['trigger'])
        if result['trigger']['episode_id'] != result['case_id'] or result['trigger']['tick'] != 2:
            raise ValueError('Fixture event belongs to another case/boundary')
    return result


def validate_truth(truth, fixture):
    fixture = validate_fixture(fixture)
    _fields(truth, 'version claim case_id protocol_sha256 source_sha256 seed regime kind subjects_by_side before_geometry after_geometry before_occupancy after_occupancy after_observations gold_target_ids')
    if type(truth['version']) is not int or truth['version'] != 1 or truth['claim'] != 'synthetic-evaluator-truth' or truth['case_id'] != fixture['case_id']:
        raise ValueError('Private truth does not belong to this development case')
    if truth['protocol_sha256'] != PROTOCOL_SHA256 or truth['source_sha256'] != SOURCE_SHA256 or truth['regime'] not in memory.RELATIONS or truth['kind'] not in KINDS:
        raise ValueError('Invalid evaluator source/protocol/mechanism')
    _integer(truth['seed'], 2**32 - 1)
    case_id, relations, letters, expected_subjects, before_geometry, after_geometry = _layout(
        truth['seed'], truth['regime'], fixture['split'], truth['kind'])
    if truth['case_id'] != case_id or truth['subjects_by_side'] != expected_subjects or truth['before_geometry'] != before_geometry or truth['after_geometry'] != after_geometry or fixture['trigger'] != _trigger(case_id, truth['kind']):
        raise ValueError('Evaluator metadata contradicts generator mechanism/counterbalancing')
    by_subject = {fact['subject_id']: fact for fact in fixture['m']['facts']}
    for side, subject in enumerate(expected_subjects):
        fact = by_subject.get(subject)
        if fact is None or fact['id'] != f'{case_id}-fact-{letters[side]}' or fact['associations'] != [{'cue_id': f'{case_id}-cue', 'relation': relations[side]}] or fact['inspection_landmark_id'] != f'{subject}-inspection' or fact['status'] != 'observed' or fact['revision'] != 0:
            raise ValueError('Public bank contradicts generator counterbalancing/seed observations')
    subjects = truth['subjects_by_side']
    if type(subjects) is not list or len(subjects) != 2 or any(type(s) is not str for s in subjects) or set(subjects) != {f['subject_id'] for f in fixture['m']['facts']}:
        raise ValueError('Evaluator side mapping has dangling subjects')
    for phase in ('before', 'after'):
        geometry = truth[f'{phase}_geometry']
        if type(geometry) is not list or len(geometry) != 20:
            raise ValueError('Evaluator geometry requires twenty circles')
        labels = memory_world.passage_status(geometry)
        expected = {subject: labels[side] for subject, side in zip(subjects, memory_world.SUBJECTS)}
        if truth[f'{phase}_occupancy'] != expected:
            raise ValueError('Occupancy disagrees with retained geometry')
        samples = fixture['before_observations'] if phase == 'before' else truth['after_observations']
        if type(samples) is not list or len(samples) != 2:
            raise ValueError('Evaluator needs two retained phase observations')
        checked = [memory.validate_observation(o) for o in samples]
        if {o['subject_id'] for o in checked} != set(subjects) or len({o['id'] for o in checked}) != 2 or any(o['episode_id'] != fixture['case_id'] or o['tick'] != (1 if phase == 'before' else 3) or o['passability'] != expected[o['subject_id']] for o in checked):
            raise ValueError('Synthetic samples disagree with retained occupancy')
    gold = gold_target_ids(fixture['m'], truth['before_occupancy'], truth['after_occupancy'], fixture['trigger'])
    if truth['gold_target_ids'] != gold:
        raise ValueError('Evaluator gold disagrees with stale observed expectations')
    return copy.deepcopy(truth)


def make_history(seed, regime, *, episodes=4, unobserved_relation=None):
    """Fixed synthetic before/after inspection schedule; no future/test inputs."""
    _integer(seed, 2**32 - 1)
    _integer(episodes, memory.MAX_EPISODES)
    if regime not in memory.RELATIONS:
        raise ValueError('Unknown historical development regime')
    if unobserved_relation is not None and unobserved_relation not in memory.RELATIONS:
        raise ValueError('Unknown unobserved relation')
    history = {'version': 1, 'episodes': []}
    for offset in range(episodes):
        fixture, truth = make_case((seed + offset) % 2**32, regime, 'development-history')
        before = {o['subject_id']: o for o in fixture['before_observations']}
        after = {o['subject_id']: o for o in truth['after_observations']}
        checks = []
        for fact in fixture['m']['facts']:
            subject, relation = fact['subject_id'], fact['associations'][0]['relation']
            sample = copy.deepcopy(after[subject])
            if relation == unobserved_relation:
                sample['passability'] = 'unobserved'
            checks.append({'subject_id': subject, 'relation': relation,
                           'before': before[subject], 'after': sample})
        history['episodes'].append({'id': fixture['case_id'], 'trigger': fixture['trigger'], 'checks': checks})
    return memory.validate_e(history)


def _relation_targets(m, trigger, relation=None):
    return [fact['id'] for fact in m['facts'] if any(a['cue_id'] == trigger['cue_id']
        and (relation is None or a['relation'] == relation) for a in fact['associations'])]


def _retrieved_relation(history, trigger):
    for episode in reversed(history['episodes']):
        if episode['trigger']['kind'] != trigger['kind'] or {c['relation'] for c in episode['checks']} != set(memory.RELATIONS):
            continue
        checks = episode['checks']
        if any(sample['passability'] == 'unobserved' for c in checks for sample in (c['before'], c['after'])):
            continue
        values = {}
        for check in checks:
            for sample in (check['before'], check['after']):
                values.setdefault((sample['subject_id'], sample['tick']), set()).add(sample['passability'])
        if any(len(v) != 1 for v in values.values()):
            continue
        changed = [c['relation'] for c in checks if c['before']['passability'] != c['after']['passability']]
        return changed[0] if len(changed) == 1 else None
    return None


def _ids(value):
    """Entity/evidence namespaces must be disjoint, not only episode names."""
    result = set()
    if type(value) is dict:
        for key, child in value.items():
            if key in ('id', 'case_id', 'episode_id', 'subject_id', 'cue_id',
                       'inspection_landmark_id', 'before_observation_id', 'observation_id') and type(child) is str:
                result.add(child)
            else:
                result.update(_ids(child))
    elif type(value) is list:
        for child in value:
            result.update(_ids(child))
    return result


def compare_conditions(fixture, own_e, swapped_e, truth, *, limit=1):
    """Evaluator wrapper; oracle/scoring alone use truth, fitting takes E only."""
    fixture, own_e, swapped_e = validate_fixture(fixture), memory.validate_e(own_e), memory.validate_e(swapped_e)
    truth = validate_truth(truth, fixture)
    _integer(limit, memory.MAX_TARGETS)
    if _ids(own_e) & _ids(swapped_e) or _ids(fixture) & (_ids(own_e) | _ids(swapped_e)):
        raise ValueError('Own/swapped/test entity and evidence IDs must be disjoint')
    own_u, swapped_u = memory.fit(own_e), memory.fit(swapped_e)
    artifacts = {'own': own_u, 'swapped': swapped_u, 'sham': copy.deepcopy(own_u),
                 'no-U': memory.artifact(method='empty-v1'), 'hand-authored': memory.artifact('local_cue')}
    m, trigger, gold = fixture['m'], fixture['trigger'], set(truth['gold_target_ids'])
    results = []
    for condition in CONDITIONS:
        runtime = {'m': m, 'trigger': trigger}
        if condition in artifacts:
            runtime['u'] = artifacts[condition]
        elif condition == 'retrieval':
            runtime['e'] = own_e
        elif condition == 'oracle':
            runtime['gold_target_ids'] = truth['gold_target_ids']
        if trigger is None:
            selection = {'event_id': None, 'target_ids': [], 'reason': 'no_rule'}
        elif condition in artifacts:
            selection = memory.select(m, trigger, artifacts[condition], limit=limit)
        else:
            if condition == 'history-independent':
                targets = [fact['id'] for fact in m['facts']]
            elif condition == 'traversal':
                targets = _relation_targets(m, trigger)
            elif condition == 'retrieval':
                relation = _retrieved_relation(own_e, trigger)
                targets = [] if relation is None else _relation_targets(m, trigger, relation)
            else:
                targets = sorted(gold)
            selection = {'event_id': trigger['id'], 'target_ids': targets[:limit],
                         'reason': 'no_match' if not targets else 'budget' if len(targets) > limit else 'matched'}
        selection = memory.validate_selection(selection, m, trigger)
        targets = set(selection['target_ids'])
        u = artifacts.get(condition)
        behavior = copy.deepcopy(runtime)
        if u is not None:
            behavior.pop('u')
            behavior['u.payload'] = u['payload']
        if trigger is None:
            behavior = {}
        results.append({'condition': condition, 'selection': selection, 'target_limit': limit,
            'u_only_eligible': condition in artifacts, 'privileged': condition == 'oracle',
            'runtime_access': list(runtime), 'runtime_input_bytes': len(memory.canonical_bytes(runtime)),
            'validation_access': list(runtime), 'behavior_access': list(behavior),
            'behavior_input_bytes': len(memory.canonical_bytes(behavior)) if behavior else 0,
            'payload_bytes': 0 if u is None else len(memory.canonical_bytes(u['payload'])),
            'envelope_bytes': 0 if u is None else len(memory.canonical_bytes(u)),
            'runtime_history_bytes': len(memory.canonical_bytes(own_e)) if condition == 'retrieval' else 0,
            'exact_set': targets == gold, 'false_targets': len(targets - gold),
            'missed_targets': len(gold - targets), 'abstained': not targets,
            'correct_abstention': not targets and not gold,
            'precision': len(targets & gold) / len(targets) if targets else None,
            'recall': len(targets & gold) / len(gold) if gold else None})
    return {'version': 1, 'claim': 'synthetic-development-comparison',
        'protocol_sha256': PROTOCOL_SHA256, 'source_sha256': SOURCE_SHA256,
        'fixture_sha256': memory.sha256(fixture), 'truth_sha256': memory.sha256(truth),
        'fixture': fixture, 'private_truth': truth,
        'case_id': fixture['case_id'], 'gold_target_ids': truth['gold_target_ids'],
        'histories': {'own': own_e, 'swapped': swapped_e},
        'history_sha256': {'own': memory.sha256(own_e), 'swapped': memory.sha256(swapped_e)},
        'history_bytes': {'own': len(memory.canonical_bytes(own_e)), 'swapped': len(memory.canonical_bytes(swapped_e))},
        'artifacts': artifacts, 'results': results}
