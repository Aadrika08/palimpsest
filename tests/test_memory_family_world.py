"""Generated scene contracts; no native feasibility or statistical qualification."""
import copy
import itertools
import math
from collections import Counter
from unittest.mock import patch

import pytest

from palimpsest import memory, memory_decision_world as world


def test_assignment_balance_and_hidden_factors_are_not_public_aliases():
    rows = [world.family_assignment(row) for row in range(48)]
    columns = ('relation_side', 'fact_first_side', 'subject_first_side',
               'route_first_side', 'schedule_index')
    bits = [{**r, 'relation': memory.RELATIONS.index(r['regime'])} for r in rows]
    for a, b in itertools.combinations(('relation', *columns), 2):
        assert Counter((r[a], r[b]) for r in bits) == dict.fromkeys(
            itertools.product((0, 1), repeat=2), 12)
    for cost in ('south', 'north', 'tie'):
        group = [r for r in bits if r['cost_stratum'] == cost]
        assert len(group) == 16
        for column in ('relation', *columns):
            assert Counter(r[column] for r in group) == {0: 8, 1: 8}
        preferred = [r['route_first_side'] if cost == 'tie' else int(cost == 'north') for r in group]
        assert sum(r['relation_side'] == p for r, p in zip(group, preferred)) == 8
    public = ('cost_stratum', 'fact_first_side', 'subject_first_side',
              'route_first_side', 'schedule_index')
    groups = {}
    for row in bits:
        groups.setdefault(tuple(row[key] for key in public), set()).add(
            (row['relation'], row['relation_side']))
    assert groups and all(hidden == set(itertools.product((0, 1), repeat=2))
                          for hidden in groups.values())


def test_real_costs_id_orders_and_twin_mapping():
    for row in range(48):
        twins = [world.make_family_case('development', 7, row, kind) for kind in ('change', 'null', 'no-event')]
        assert len({c['case_id'] for c in twins}) == 3
        assert len({c['family_id'] for c in twins}) == len({c['seed'] for c in twins}) == 1
        assert len({memory.sha256(c['geometry']) for c in twins}) == 1
        entity_sets = []
        for c in twins:
            assert world.validate_case(c) == c
            a = world.family_assignment(row)
            sides = c['subjects_by_side']
            graph = world.public_graph(c)
            assert graph['version'] == 3
            assert not set(('geometry', 'factors', 'closure_subject_id', 'landmarks')) & set(graph)
            assert sides[a['subject_first_side']] == min(sides)
            assert min(c['facts'], key=lambda f: f['id'])['subject_id'] == sides[a['fact_first_side']]
            assert graph['routes'][0]['subject_id'] == sides[a['route_first_side']]
            learned = next(f for f in c['facts'] if f['associations'][0]['relation'] == c['regime'])
            assert learned['subject_id'] == sides[a['relation_side']]
            assert c['closure_subject_id'] == (learned['subject_id'] if c['kind'] == 'change' else None)
            assert c['event_enabled'] == (c['kind'] != 'no-event')
            costs = {}
            for route in graph['routes']:
                assert len(route['waypoint_ids']) == 5
                assert route['waypoint_ids'][2].endswith('-detour')
                points = [c['landmarks'][i] for i in [c['decision_landmark_id'], *route['waypoint_ids']]]
                assert route['cost'] == sum(math.dist(p, q) for p, q in zip(points, points[1:]))
                costs[sides.index(route['subject_id'])] = route['cost']
            if a['cost_stratum'] == 'tie':
                assert costs[0] == costs[1]
            else:
                assert min(costs, key=costs.get) == int(a['cost_stratum'] == 'north')
            entity_sets.append(set(c['landmarks']) | set(sides) | {f['id'] for f in c['facts']} | {c['cue_id']})
        assert all(not a & b for a, b in itertools.combinations(entity_sets, 2))


def test_public_graph_and_initial_memory_do_not_determine_future_closure():
    alternatives = {}
    for row in range(48):
        case = world.make_family_case('development', 0, row, 'change')
        graph, subjects = world.public_graph(case), case['subjects_by_side']
        costs = {subjects.index(route['subject_id']): route['cost'] for route in graph['routes']}
        cost = 'tie' if costs[0] == costs[1] else ('south' if costs[0] < costs[1] else 'north')
        local_side = subjects.index(next(fact['subject_id'] for fact in case['facts']
            if fact['associations'][0]['relation'] == 'local_cue'))
        signature = (cost, subjects.index(min(subjects)),
            subjects.index(graph['routes'][0]['subject_id']),
            subjects.index(min(case['facts'], key=lambda fact: fact['id'])['subject_id']),
            world.FAMILY_PROFILE_HASHES.index(graph['profile_sha256']), local_side)
        alternatives.setdefault(signature, set()).add(
            (subjects.index(case['closure_subject_id']), case['regime']))
    assert alternatives and all({side for side, _ in choices} == {0, 1}
                                and {regime for _, regime in choices} == set(memory.RELATIONS)
                                for choices in alternatives.values())


def test_all_finite_geometry_combinations_pass_analytic_guards(monkeypatch):
    # Exhaust the declared catalog with synthetic draw substitution, not native observations.
    choices = world.FAMILY_DESIGN['geometry']
    for x, ex, radius, pair in itertools.product(choices['detour_x'], choices['exit_x'],
                                                choices['loop_radius'], choices['offset_pair']):
        for row in (0, 16):
            draws = {'detour_x': x, 'exit_x': ex, 'loop_radius': radius, 'offset_pair': pair}
            monkeypatch.setattr(world, '_family_pick', lambda seed, label, values: copy.deepcopy(draws[label]))
            case = world.make_family_case('development', 0, row, 'change')
            assert world.geometry_check(case)['valid'], (draws, row, world.geometry_check(case))
    for x, ex, radius, offset in itertools.product(choices['detour_x'], choices['exit_x'],
                                                  choices['loop_radius'], choices['tie_offset']):
        draws = {'detour_x': x, 'exit_x': ex, 'loop_radius': radius, 'tie_offset': offset}
        monkeypatch.setattr(world, '_family_pick', lambda seed, label, values: copy.deepcopy(draws[label]))
        case = world.make_family_case('development', 0, 32, 'null')
        assert world.geometry_check(case)['valid'], (draws, world.geometry_check(case))


@pytest.mark.parametrize('split,block,row,kind', [('train', 0, 0, 'change'), ('development', True, 0, 'change'),
    ('development', -1, 0, 'change'), ('development', 2**23, 0, 'change'),
    ('development', 0, True, 'change'), ('development', 0, 48, 'change'), ('development', 0, 0, 'other')])
def test_invalid_generator_inputs(split, block, row, kind):
    with pytest.raises(ValueError):
        world.make_family_case(split, block, row, kind)


def test_disjoint_split_seed_partitions_and_determinism():
    seeds, ids = set(), set()
    for split, block, row in itertools.product(('development', 'held-out'), (0, 2**23-1), (0, 47)):
        c = world.make_family_case(split, block, row, 'change')
        assert c == world.make_family_case(split, block, row, 'change')
        lower = 2**29 if split == 'development' else 2**30
        assert lower <= c['seed'] < lower + 2**29
        assert c['seed'] not in seeds and c['family_id'] not in ids
        seeds.add(c['seed']); ids.add(c['family_id'])


@pytest.mark.parametrize('field', ['version', 'row', 'regime', 'seed', 'profile_sha256',
    'family_id', 'geometry', 'route_ids_by_side', 'closure_subject_id', 'case_sha256'])
def test_rehashed_case_mutations_are_rejected(field):
    c = world.make_family_case('development', 0, 0, 'change')
    c[field] = {'version': 2, 'row': 1, 'seed': c['seed']+1, 'geometry': {},
                'route_ids_by_side': c['route_ids_by_side'][::-1]}.get(field, 'forged')
    if field != 'case_sha256':
        c['case_sha256'] = memory.sha256({k: v for k, v in c.items() if k != 'case_sha256'})
    with pytest.raises(ValueError):
        world.validate_case(c)


def test_family_profile_cannot_enter_legacy_generator():
    with pytest.raises(ValueError):
        world.make_case(0, 'local_cue', 'change', profile_sha256=world.FAMILY_PROFILE_HASHES[0])


def test_all_84_legacy_case_and_graph_hashes_remain_identical():
    rows = []
    for profile, regime, kind, mirrored in itertools.product(
            (world.PROFILE_SHA256, *world.WAYPOINT_PROFILE_HASHES, *world.TRAVEL_PROFILE_HASHES),
            memory.RELATIONS, ('change', 'null', 'no-event'), (False, True)):
        case = world.make_case(123, regime, kind, mirrored, profile_sha256=profile)
        rows.append({'profile': profile, 'regime': regime, 'kind': kind, 'mirrored': mirrored,
                     'case': case['case_sha256'], 'graph': case['graph_sha256']})
    assert memory.sha256(rows) == '6ecaf341c9270bf422a133a31c3782ae6f208263dad5968be9ea0240ca8faec8'


def test_world_schedule_and_reconstructed_apertures_follow_actual_side():
    for row, kind in itertools.product(range(48), ('change', 'null', 'no-event')):
        case = world.make_family_case('development', 0, row, kind)
        state = world.initial_state(case)
        state['last_tick'] = 9
        state = world.arm(state, 10, 'a'*64)
        schedule = world.registered_profile(case['profile_sha256'])['arm_schedule']
        assert state['event_tick'] == (None if kind == 'no-event' else 10+schedule['event_offset'])
        assert state['decision_tick'] == 10+schedule['decision_offset']
        bad = copy.deepcopy(state)
        bad['decision_tick'] += 1
        with pytest.raises(ValueError):
            world.validate_state(bad)
        with patch.object(world, 'apply_intervention', side_effect=lambda env, edit: edit) as apply:
            for tick in range(10, state['decision_tick']+1):
                state, events = world.advance_world(None, state, tick)
                assert bool(events) == (tick == state['event_tick'])
                assert world.advance_world(None, state, tick) == (state, [])
                assert world.audit_inputs(state, case['start_pose']) == world.reconstruct_inputs(
                    case, case['start_pose'], tick, event_tick=state['event_tick'], gate_result=state['gate_result'])
            assert apply.call_count == int(kind == 'change')
            if kind == 'change':
                side = case['subjects_by_side'].index(case['closure_subject_id'])
                assert apply.call_args.args[1] == {'kind': 'move_obstacle', 'index': len(world.POSTS)+side,
                                                  'xy': world.CLOSED_GATES[side]}
        symbolic, _, _ = world.audit_inputs(state, case['start_pose'])
        blocked = [p['subject_id'] for p in symbolic['passages'] if p['passability'] == 'blocked']
        assert blocked == ([case['closure_subject_id']] if kind == 'change' else [])


def test_rejected_native_placement_stays_rejected_in_audit():
    case = world.make_family_case('development', 0, 2, 'change')
    state = world.initial_state(case)
    state['last_tick'] = 9
    state = world.arm(state, 10, 'a'*64)
    with patch.object(world, 'apply_intervention', side_effect=ValueError('synthetic refusal')):
        for tick in range(10, state['event_tick']+1):
            state, events = world.advance_world(None, state, tick)
    assert state['gate_result'] == 'rejected'
    assert events[-1]['kind'] == 'memory_gate_rejected'
    assert all(p['passability'] == 'open' for p in world.audit_inputs(state, case['start_pose'])[0]['passages'])
